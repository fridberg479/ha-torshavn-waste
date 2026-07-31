from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import urllib.parse

import pytest


ARCGIS_FILE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "torshavn_waste"
    / "arcgis.py"
)

spec = importlib.util.spec_from_file_location(
    "torshavn_waste_arcgis",
    ARCGIS_FILE,
)

if spec is None or spec.loader is None:
    raise RuntimeError(
        f"Could not load ArcGIS module from {ARCGIS_FILE}"
    )

arcgis_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = arcgis_module
spec.loader.exec_module(arcgis_module)

ArcGISDataError = arcgis_module.ArcGISDataError
GeneralWasteArea = arcgis_module.GeneralWasteArea
build_query_url = arcgis_module.build_query_url
parse_general_waste_response = (
    arcgis_module.parse_general_waste_response
)


VALID_RESPONSE = {
    "features": [
        {
            "attributes": {
                "OBJECTID": 1226,
                "name": None,
                "city": "Tórshavn",
                "zip": 100,
                "car_id": 3,
                "day": 4,
                "GlobalID": (
                    "{BA03F4B3-0900-4221-"
                    "97E3-D0811D8923ED}"
                ),
            }
        }
    ]
}


def test_parse_valid_response() -> None:
    results = parse_general_waste_response(
        VALID_RESPONSE
    )

    assert len(results) == 1

    area = results[0]

    assert isinstance(area, GeneralWasteArea)
    assert area.object_id == 1226
    assert area.area_name is None
    assert area.city == "Tórshavn"
    assert area.zip_code == 100
    assert area.route_id == 3
    assert area.weekday == 4
    assert area.weekday_name == "hósdagur"
    assert area.global_id == (
        "{BA03F4B3-0900-4221-"
        "97E3-D0811D8923ED}"
    )


def test_parse_empty_feature_list() -> None:
    results = parse_general_waste_response(
        {
            "features": [],
        }
    )

    assert results == ()


def test_parse_multiple_features() -> None:
    response = {
        "features": [
            VALID_RESPONSE["features"][0],
            {
                "attributes": {
                    "OBJECTID": 1227,
                    "name": "Test area",
                    "city": "Argir",
                    "zip": 160,
                    "car_id": 6,
                    "day": 2,
                    "GlobalID": "{TEST-ID}",
                }
            },
        ]
    }

    results = parse_general_waste_response(
        response
    )

    assert len(results) == 2
    assert results[0].weekday_name == "hósdagur"
    assert results[1].weekday_name == "týsdagur"
    assert results[1].city == "Argir"


def test_parse_arcgis_error() -> None:
    response = {
        "error": {
            "code": 400,
            "message": "Invalid query",
        }
    }

    with pytest.raises(
        ArcGISDataError,
        match="ArcGIS returned an error",
    ):
        parse_general_waste_response(
            response
        )


def test_parse_requires_feature_list() -> None:
    with pytest.raises(
        ArcGISDataError,
        match="valid feature list",
    ):
        parse_general_waste_response(
            {}
        )


def test_parse_rejects_invalid_feature() -> None:
    with pytest.raises(
        ArcGISDataError,
        match="feature is invalid",
    ):
        parse_general_waste_response(
            {
                "features": [
                    "not a feature",
                ],
            }
        )


def test_parse_rejects_invalid_attributes() -> None:
    with pytest.raises(
        ArcGISDataError,
        match="attributes are invalid",
    ):
        parse_general_waste_response(
            {
                "features": [
                    {
                        "attributes": None,
                    }
                ],
            }
        )


def test_parse_rejects_missing_weekday() -> None:
    response = {
        "features": [
            {
                "attributes": {
                    "OBJECTID": 1,
                    "day": None,
                }
            }
        ]
    }

    with pytest.raises(
        ArcGISDataError,
        match="weekday is invalid",
    ):
        parse_general_waste_response(
            response
        )


def test_parse_rejects_unsupported_weekday() -> None:
    response = {
        "features": [
            {
                "attributes": {
                    "OBJECTID": 1,
                    "day": 7,
                }
            }
        ]
    }

    with pytest.raises(
        ArcGISDataError,
        match="unsupported weekday",
    ):
        parse_general_waste_response(
            response
        )


def test_build_query_url_uses_wgs84_point() -> None:
    url = build_query_url(
        latitude=61.995070,
        longitude=-6.797773,
        radius_metres=25,
    )

    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(
        parsed.query
    )

    assert parsed.scheme == "https"
    assert query["geometryType"] == [
        "esriGeometryPoint"
    ]
    assert query["inSR"] == ["4326"]
    assert query["distance"] == ["25"]
    assert query["units"] == [
        "esriSRUnit_Meter"
    ]

    geometry = json.loads(
        query["geometry"][0]
    )

    assert geometry["x"] == pytest.approx(
        -6.797773
    )
    assert geometry["y"] == pytest.approx(
        61.995070
    )
    assert geometry["spatialReference"] == {
        "wkid": 4326
    }


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (-91, 0),
        (91, 0),
        (0, -181),
        (0, 181),
    ],
)
def test_build_query_url_rejects_invalid_coordinates(
    latitude: float,
    longitude: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="Invalid",
    ):
        build_query_url(
            latitude=latitude,
            longitude=longitude,
        )


def test_build_query_url_rejects_invalid_radius() -> None:
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        build_query_url(
            latitude=61.995070,
            longitude=-6.797773,
            radius_metres=0,
        )