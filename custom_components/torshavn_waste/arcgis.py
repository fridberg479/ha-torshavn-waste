"""ArcGIS client for general waste collection in Tórshavn."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
import urllib.error
import urllib.parse
import urllib.request


QUERY_URL = (
    "https://gis.torshavn.fo/arcgis/rest/services/"
    "ruskinnsavning/ruskinnsavning_alment/MapServer/0/query"
)

DAY_NAMES = {
    1: "mánadagur",
    2: "týsdagur",
    3: "mikudagur",
    4: "hósdagur",
    5: "fríggjadagur",
}


class ArcGISWasteError(Exception):
    """Base error for ArcGIS waste collection operations."""


class ArcGISConnectionError(ArcGISWasteError):
    """Raised when the ArcGIS service cannot be reached."""


class ArcGISDataError(ArcGISWasteError):
    """Raised when ArcGIS returns invalid or unexpected data."""


@dataclass(frozen=True, slots=True)
class GeneralWasteArea:
    """One general-waste collection area."""

    object_id: int | None
    area_name: str | None
    city: str | None
    zip_code: int | str | None
    route_id: int | str | None
    weekday: int
    global_id: str | None

    @property
    def weekday_name(self) -> str:
        """Return the Faroese weekday name."""

        return DAY_NAMES.get(
            self.weekday,
            "ókendur dagur",
        )


def build_query_url(
    latitude: float,
    longitude: float,
    radius_metres: float = 25,
) -> str:
    """
    Build an ArcGIS query URL.

    The input coordinates use WGS84. ArcGIS performs the
    coordinate conversion on the server.
    """

    if not -90 <= latitude <= 90:
        raise ValueError(
            f"Invalid latitude: {latitude}"
        )

    if not -180 <= longitude <= 180:
        raise ValueError(
            f"Invalid longitude: {longitude}"
        )

    if radius_metres <= 0:
        raise ValueError(
            "radius_metres must be greater than zero."
        )

    geometry = {
        "x": longitude,
        "y": latitude,
        "spatialReference": {
            "wkid": 4326,
        },
    }

    params = {
        "f": "json",
        "returnGeometry": "false",
        "spatialRel": (
            "esriSpatialRelIntersects"
        ),
        "geometry": json.dumps(
            geometry,
            separators=(",", ":"),
        ),
        "geometryType": (
            "esriGeometryPoint"
        ),
        "inSR": "4326",
        "distance": str(radius_metres),
        "units": "esriSRUnit_Meter",
        "outFields": (
            "OBJECTID,name,city,zip,"
            "car_id,day,GlobalID"
        ),
    }

    return (
        f"{QUERY_URL}?"
        f"{urllib.parse.urlencode(params)}"
    )


def fetch_general_waste_areas(
    latitude: float,
    longitude: float,
    radius_metres: float = 25,
    timeout: float = 20,
) -> tuple[GeneralWasteArea, ...]:
    """Fetch general-waste collection areas near a coordinate."""

    url = build_query_url(
        latitude=latitude,
        longitude=longitude,
        radius_metres=radius_metres,
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "ha-torshavn-waste/0.2"
            ),
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            raw_data: Any = json.load(response)

    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        OSError,
    ) as error:
        raise ArcGISConnectionError(
            f"Could not contact ArcGIS: {error}"
        ) from error

    return parse_general_waste_response(
        raw_data
    )


def parse_general_waste_response(
    raw_data: Any,
) -> tuple[GeneralWasteArea, ...]:
    """Parse and validate an ArcGIS query response."""

    if not isinstance(raw_data, dict):
        raise ArcGISDataError(
            "ArcGIS response must be a JSON object."
        )

    error_data = raw_data.get("error")

    if error_data is not None:
        raise ArcGISDataError(
            "ArcGIS returned an error: "
            f"{json.dumps(error_data, ensure_ascii=False)}"
        )

    features = raw_data.get("features")

    if not isinstance(features, list):
        raise ArcGISDataError(
            "ArcGIS response does not contain "
            "a valid feature list."
        )

    results: list[GeneralWasteArea] = []

    for feature in features:
        if not isinstance(feature, dict):
            raise ArcGISDataError(
                "ArcGIS feature is invalid."
            )

        attributes = feature.get(
            "attributes"
        )

        if not isinstance(attributes, dict):
            raise ArcGISDataError(
                "ArcGIS feature attributes are invalid."
            )

        weekday = attributes.get("day")

        if not isinstance(weekday, int):
            raise ArcGISDataError(
                "ArcGIS collection weekday is invalid."
            )

        if weekday not in DAY_NAMES:
            raise ArcGISDataError(
                "ArcGIS returned an unsupported "
                f"weekday: {weekday}"
            )

        results.append(
            GeneralWasteArea(
                object_id=_optional_int(
                    attributes.get("OBJECTID")
                ),
                area_name=_optional_string(
                    attributes.get("name")
                ),
                city=_optional_string(
                    attributes.get("city")
                ),
                zip_code=attributes.get("zip"),
                route_id=attributes.get("car_id"),
                weekday=weekday,
                global_id=_optional_string(
                    attributes.get("GlobalID")
                ),
            )
        )

    return tuple(results)


def _optional_string(
    value: Any,
) -> str | None:
    """Return a stripped string or None."""

    if value is None:
        return None

    text = str(value).strip()

    return text or None


def _optional_int(
    value: Any,
) -> int | None:
    """Return an integer or None."""

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None