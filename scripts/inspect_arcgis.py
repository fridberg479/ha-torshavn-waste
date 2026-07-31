from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from pyproj import Transformer


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

TRANSFORMER = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:5316",
    always_xy=True,
)


def fetch_waste_area(
    latitude: float,
    longitude: float,
    radius_metres: float = 25,
) -> dict[str, Any]:
    """Fetch waste collection area near a coordinate."""

    x, y = TRANSFORMER.transform(longitude, latitude)

    geometry = {
        "xmin": x - radius_metres,
        "ymin": y - radius_metres,
        "xmax": x + radius_metres,
        "ymax": y + radius_metres,
        "spatialReference": {
            "wkid": 5316,
            "latestWkid": 5316,
        },
    }

    params = {
        "f": "json",
        "returnGeometry": "false",
        "spatialRel": "esriSpatialRelIntersects",
        "geometry": json.dumps(
            geometry,
            separators=(",", ":"),
        ),
        "geometryType": "esriGeometryEnvelope",
        "inSR": "5316",
        "outFields": (
            "OBJECTID,name,city,zip,car_id,day,GlobalID"
        ),
    }

    url = f"{QUERY_URL}?{urllib.parse.urlencode(params)}"

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ha-torshavn-waste-development/0.1",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        result: dict[str, Any] = json.load(response)

    if "error" in result:
        raise RuntimeError(
            json.dumps(
                result["error"],
                ensure_ascii=False,
            )
        )

    return result


def simplify_result(
    result: dict[str, Any],
) -> list[dict[str, Any]]:
    """Convert the ArcGIS response to a simpler structure."""

    simplified: list[dict[str, Any]] = []

    for feature in result.get("features", []):
        attributes = feature.get("attributes", {})

        day_number = attributes.get("day")

        simplified.append(
            {
                "object_id": attributes.get("OBJECTID"),
                "area_name": attributes.get("name"),
                "city": attributes.get("city"),
                "zip": attributes.get("zip"),
                "route_id": attributes.get("car_id"),
                "weekday": day_number,
                "weekday_name": DAY_NAMES.get(
                    day_number,
                    "ókendur dagur",
                ),
                "global_id": attributes.get("GlobalID"),
            }
        )

    return simplified


def print_summary(
    areas: list[dict[str, Any]],
) -> None:
    """Print a readable summary of the returned areas."""

    print(f"\nFound {len(areas)} waste collection area(s):\n")

    for index, area in enumerate(areas, start=1):
        print(f"Result {index}")
        print(f"  Area name: {area['area_name']}")
        print(f"  City: {area['city']}")
        print(f"  ZIP: {area['zip']}")
        print(
            "  Collection day: "
            f"{area['weekday_name']} ({area['weekday']})"
        )
        print(f"  Route/car ID: {area['route_id']}")
        print(f"  OBJECTID: {area['object_id']}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect Tórshavn Municipality waste collection data "
            "for a latitude and longitude."
        )
    )

    parser.add_argument(
        "latitude",
        type=float,
        help="Latitude in WGS84, for example 61.9951.",
    )

    parser.add_argument(
        "longitude",
        type=float,
        help="Longitude in WGS84, for example -6.7978.",
    )

    parser.add_argument(
        "--radius",
        type=float,
        default=25,
        help="Search radius in metres. Default: 25.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Optional file where the simplified JSON is saved.",
    )

    parser.add_argument(
        "--raw-output",
        type=Path,
        help="Optional file where the raw ArcGIS response is saved.",
    )

    args = parser.parse_args()

    try:
        raw_result = fetch_waste_area(
            latitude=args.latitude,
            longitude=args.longitude,
            radius_metres=args.radius,
        )
    except Exception as error:
        print(
            f"Error requesting ArcGIS data: {error}",
            file=sys.stderr,
        )
        return 1

    areas = simplify_result(raw_result)

    print_summary(areas)

    simplified_json = json.dumps(
        areas,
        indent=2,
        ensure_ascii=False,
    )

    print("Simplified response:")
    print(simplified_json)

    if args.output:
        args.output.write_text(
            simplified_json + "\n",
            encoding="utf-8",
        )

        print(
            f"\nSaved simplified response to {args.output}"
        )

    if args.raw_output:
        raw_json = json.dumps(
            raw_result,
            indent=2,
            ensure_ascii=False,
        )

        args.raw_output.write_text(
            raw_json + "\n",
            encoding="utf-8",
        )

        print(
            f"Saved raw response to {args.raw_output}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())