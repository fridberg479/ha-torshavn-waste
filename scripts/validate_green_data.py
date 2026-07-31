from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any


EXPECTED_AREAS = {"1", "2", "3", "4", "5", "6"}


class ValidationError(Exception):
    """Raised when the calendar data is invalid."""


def load_json(path: Path) -> dict[str, Any]:
    """Load and return a JSON object."""

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValidationError(
            f"Fekk ikki lisið fíluna: {error}"
        ) from error

    try:
        data = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValidationError(
            "JSON-feilur á linju "
            f"{error.lineno}, teigi {error.colno}: "
            f"{error.msg}"
        ) from error

    if not isinstance(data, dict):
        raise ValidationError(
            "Ovasta stigið í JSON-fíluni skal vera eitt object."
        )

    return data


def require_dict(
    value: Any,
    field_name: str,
) -> dict[str, Any]:
    """Require a dictionary value."""

    if not isinstance(value, dict):
        raise ValidationError(
            f"{field_name} skal vera eitt object."
        )

    return value


def require_list(
    value: Any,
    field_name: str,
) -> list[Any]:
    """Require a list value."""

    if not isinstance(value, list):
        raise ValidationError(
            f"{field_name} skal vera ein listi."
        )

    return value


def validate_top_level(
    data: dict[str, Any],
) -> int:
    """Validate top-level metadata and return the calendar year."""

    schema_version = data.get("schema_version")

    if schema_version != 1:
        raise ValidationError(
            "schema_version skal vera 1."
        )

    year = data.get("year")

    if not isinstance(year, int):
        raise ValidationError(
            "year skal vera eitt heilt tal."
        )

    if not 2000 <= year <= 2100:
        raise ValidationError(
            f"year hevur eitt óvæntað virði: {year}"
        )

    source = require_dict(
        data.get("source"),
        "source",
    )

    for field_name in (
        "title",
        "organisation",
        "file",
        "generated_at",
    ):
        value = source.get(field_name)

        if not isinstance(value, str) or not value.strip():
            raise ValidationError(
                f"source.{field_name} skal vera ein tekstur."
            )

    return year


def validate_collection_dates(
    values: Any,
    area_number: str,
    year: int,
) -> list[str]:
    """Validate collection dates for one area."""

    dates = require_list(
        values,
        f"areas.{area_number}.collection_dates",
    )

    if not dates:
        raise ValidationError(
            f"Øki {area_number} hevur ongar tømingardagar."
        )

    parsed_dates: list[date] = []
    seen: set[str] = set()

    for index, value in enumerate(dates):
        field_name = (
            f"areas.{area_number}.collection_dates[{index}]"
        )

        if not isinstance(value, str):
            raise ValidationError(
                f"{field_name} skal vera ein ISO-dato."
            )

        if value in seen:
            raise ValidationError(
                f"Øki {area_number} hevur dupultan dato: {value}"
            )

        seen.add(value)

        try:
            parsed = date.fromisoformat(value)
        except ValueError as error:
            raise ValidationError(
                f"Ógyldigur dato í {field_name}: {value}"
            ) from error

        if parsed.year != year:
            raise ValidationError(
                f"Datum {value} í øki {area_number} "
                f"hoyrir ikki til {year}."
            )

        parsed_dates.append(parsed)

    if parsed_dates != sorted(parsed_dates):
        raise ValidationError(
            f"Tømingardagarnir í øki {area_number} "
            "eru ikki í dato-raðfylgju."
        )

    return [
        parsed.isoformat()
        for parsed in parsed_dates
    ]


def validate_streets(
    values: Any,
    area_number: str,
) -> list[str]:
    """Validate streets for one area."""

    streets = require_list(
        values,
        f"areas.{area_number}.streets",
    )

    if not streets:
        raise ValidationError(
            f"Øki {area_number} hevur ongar gøtur."
        )

    cleaned: list[str] = []
    seen: set[str] = set()

    for index, value in enumerate(streets):
        field_name = (
            f"areas.{area_number}.streets[{index}]"
        )

        if not isinstance(value, str):
            raise ValidationError(
                f"{field_name} skal vera ein tekstur."
            )

        street = value.strip()

        if not street:
            raise ValidationError(
                f"{field_name} er tómur."
            )

        key = street.casefold()

        if key in seen:
            raise ValidationError(
                f"Øki {area_number} hevur somu gøtu "
                f"tvær ferðir: {street}"
            )

        seen.add(key)
        cleaned.append(street)

    return cleaned


def validate_areas(
    data: dict[str, Any],
    year: int,
) -> tuple[
    dict[str, list[str]],
    dict[str, list[str]],
]:
    """Validate all areas."""

    areas = require_dict(
        data.get("areas"),
        "areas",
    )

    area_keys = set(areas)

    missing = EXPECTED_AREAS - area_keys
    extra = area_keys - EXPECTED_AREAS

    if missing:
        raise ValidationError(
            "Hesi øki mangla: "
            + ", ".join(sorted(missing))
        )

    if extra:
        raise ValidationError(
            "Ókend øki funnin: "
            + ", ".join(sorted(extra))
        )

    streets_by_area: dict[str, list[str]] = {}
    dates_by_area: dict[str, list[str]] = {}

    for area_number in sorted(
        EXPECTED_AREAS,
        key=int,
    ):
        area = require_dict(
            areas.get(area_number),
            f"areas.{area_number}",
        )

        streets_by_area[area_number] = validate_streets(
            area.get("streets"),
            area_number,
        )

        dates_by_area[area_number] = (
            validate_collection_dates(
                area.get("collection_dates"),
                area_number,
                year,
            )
        )

    return streets_by_area, dates_by_area


def validate_bag_delivery(
    value: Any,
    field_name: str,
) -> None:
    """Validate one bag-delivery section."""

    section = require_dict(
        value,
        field_name,
    )

    months = require_list(
        section.get("months"),
        f"{field_name}.months",
    )

    if months != [4, 10]:
        raise ValidationError(
            f"{field_name}.months skal vera [4, 10]."
        )

    exact_dates_known = section.get(
        "exact_dates_known"
    )

    if exact_dates_known is not False:
        raise ValidationError(
            f"{field_name}.exact_dates_known "
            "skal vera false."
        )

    description = section.get("description")

    if not isinstance(description, str) or not description.strip():
        raise ValidationError(
            f"{field_name}.description skal vera ein tekstur."
        )


def validate_bag_deliveries(
    data: dict[str, Any],
) -> None:
    """Validate bag-delivery metadata."""

    deliveries = require_dict(
        data.get("bag_deliveries"),
        "bag_deliveries",
    )

    validate_bag_delivery(
        deliveries.get("grey_bags"),
        "bag_deliveries.grey_bags",
    )

    validate_bag_delivery(
        deliveries.get("red_bag"),
        "bag_deliveries.red_bag",
    )


def find_cross_area_streets(
    streets_by_area: dict[str, list[str]],
) -> dict[str, dict[str, Any]]:
    """Find street names that occur in multiple areas."""

    locations: dict[str, set[str]] = defaultdict(set)
    display_names: dict[str, str] = {}

    for area_number, streets in streets_by_area.items():
        for street in streets:
            key = street.casefold()

            locations[key].add(area_number)
            display_names.setdefault(
                key,
                street,
            )

    result: dict[str, dict[str, Any]] = {}

    for key, areas in locations.items():
        if len(areas) <= 1:
            continue

        display_name = display_names[key]

        result[display_name] = {
            "areas": sorted(
                areas,
                key=int,
            )
        }

    return dict(
        sorted(
            result.items(),
            key=lambda item: item[0].casefold(),
        )
    )


def print_summary(
    data: dict[str, Any],
    streets_by_area: dict[str, list[str]],
    dates_by_area: dict[str, list[str]],
    shared_streets: dict[str, dict[str, Any]],
) -> None:
    """Print a validation summary."""

    print()
    print("Validering: OK")
    print()
    print(f"Ár: {data['year']}")
    print(
        f"Schema-version: {data['schema_version']}"
    )
    print()

    total_streets = 0
    total_dates = 0

    for area_number in sorted(
        EXPECTED_AREAS,
        key=int,
    ):
        street_count = len(
            streets_by_area[area_number]
        )
        date_count = len(
            dates_by_area[area_number]
        )

        total_streets += street_count
        total_dates += date_count

        print(
            f"Øki {area_number}: "
            f"{street_count} gøtur, "
            f"{date_count} tømingardagar"
        )

    print()
    print(
        f"Gøtuskrásetingar í alt: {total_streets}"
    )
    print(
        f"Tømingardagar í alt: {total_dates}"
    )
    print(
        "Gøtur í fleiri økjum: "
        f"{len(shared_streets)}"
    )

    if shared_streets:
        print()
        print(
            "Ávaringar — krevja val av øki "
            "ella húsanummari:"
        )

        for street, information in shared_streets.items():
            areas = ", ".join(
                information["areas"]
            )

            print(
                f"  - {street}: øki {areas}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate generated green-calendar JSON data."
        )
    )

    parser.add_argument(
        "json_file",
        nargs="?",
        type=Path,
        default=Path(
            "data/green_calendar_2026.json"
        ),
        help=(
            "JSON file to validate. Default: "
            "data/green_calendar_2026.json"
        ),
    )

    parser.add_argument(
        "--warnings-output",
        type=Path,
        help=(
            "Optional JSON file where streets in "
            "multiple areas are saved."
        ),
    )

    args = parser.parse_args()

    if not args.json_file.is_file():
        print(
            "JSON-fílan varð ikki funnin: "
            f"{args.json_file}",
            file=sys.stderr,
        )
        return 1

    try:
        data = load_json(args.json_file)
        year = validate_top_level(data)

        streets_by_area, dates_by_area = (
            validate_areas(
                data,
                year,
            )
        )

        validate_bag_deliveries(data)

        shared_streets = find_cross_area_streets(
            streets_by_area
        )

    except ValidationError as error:
        print(
            f"Valideringsfeilur: {error}",
            file=sys.stderr,
        )
        return 1

    print_summary(
        data,
        streets_by_area,
        dates_by_area,
        shared_streets,
    )

    if args.warnings_output:
        args.warnings_output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        args.warnings_output.write_text(
            json.dumps(
                {
                    "year": year,
                    "streets_in_multiple_areas": (
                        shared_streets
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        print()
        print(
            "Ávaringar vórðu goymdar í: "
            f"{args.warnings_output}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())