from __future__ import annotations

from datetime import date
import importlib.util
from pathlib import Path
import sys

import pytest


API_FILE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "torshavn_waste"
    / "api.py"
)

spec = importlib.util.spec_from_file_location(
    "torshavn_waste_api",
    API_FILE,
)

if spec is None or spec.loader is None:
    raise RuntimeError(
        f"Could not load API module from {API_FILE}"
    )

api_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = api_module
spec.loader.exec_module(api_module)

GreenCalendar = api_module.GreenCalendar
GreenCalendarError = api_module.GreenCalendarError


DATA_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "green_calendar_2026.json"
)


@pytest.fixture
def calendar() -> GreenCalendar:
    """Return a calendar loaded from the repository data."""

    return GreenCalendar(DATA_FILE)


def test_calendar_year(
    calendar: GreenCalendar,
) -> None:
    assert calendar.year == 2026


def test_available_areas(
    calendar: GreenCalendar,
) -> None:
    assert calendar.areas == (1, 2, 3, 4, 5, 6)


def test_find_unambiguous_street(
    calendar: GreenCalendar,
) -> None:
    match = calendar.find_street("Hoyvíksvegur")

    assert match is not None
    assert match.street == "Hoyvíksvegur"
    assert match.areas == (3,)
    assert match.is_ambiguous is False


def test_find_street_is_case_insensitive(
    calendar: GreenCalendar,
) -> None:
    match = calendar.find_street("HOYVÍKSVEGUR")

    assert match is not None
    assert match.areas == (3,)


def test_find_street_ignores_extra_whitespace(
    calendar: GreenCalendar,
) -> None:
    match = calendar.find_street(
        "  Hoyvíksvegur  "
    )

    assert match is not None
    assert match.areas == (3,)


def test_find_ambiguous_street(
    calendar: GreenCalendar,
) -> None:
    match = calendar.find_street("Oyggjarvegur")

    assert match is not None
    assert match.areas == (1, 4, 6)
    assert match.is_ambiguous is True


def test_unknown_street_returns_none(
    calendar: GreenCalendar,
) -> None:
    assert (
        calendar.find_street(
            "Hetta gøtunavnið finst ikki"
        )
        is None
    )


def test_search_streets(
    calendar: GreenCalendar,
) -> None:
    matches = calendar.search_streets(
        "Hoyvíks"
    )

    assert matches
    assert matches[0].street == "Hoyvíksvegur"


def test_next_collection_for_hoyviksvegur(
    calendar: GreenCalendar,
) -> None:
    result = calendar.next_collection_for_street(
        "Hoyvíksvegur",
        from_date=date(2026, 7, 31),
    )

    assert result is not None
    assert result.area == 3
    assert result.collection_date == date(
        2026,
        8,
        11,
    )
    assert result.days_until == 11


def test_next_collection_includes_today(
    calendar: GreenCalendar,
) -> None:
    result = calendar.next_collection(
        area=3,
        from_date=date(2026, 8, 11),
        include_today=True,
    )

    assert result is not None
    assert result.collection_date == date(
        2026,
        8,
        11,
    )
    assert result.days_until == 0


def test_next_collection_can_exclude_today(
    calendar: GreenCalendar,
) -> None:
    result = calendar.next_collection(
        area=3,
        from_date=date(2026, 8, 11),
        include_today=False,
    )

    assert result is not None
    assert result.collection_date == date(
        2026,
        9,
        22,
    )


def test_no_collection_after_last_date(
    calendar: GreenCalendar,
) -> None:
    result = calendar.next_collection(
        area=1,
        from_date=date(2026, 12, 31),
    )

    assert result is None


def test_ambiguous_street_requires_area(
    calendar: GreenCalendar,
) -> None:
    with pytest.raises(
        GreenCalendarError,
        match="multiple areas",
    ):
        calendar.next_collection_for_street(
            "Oyggjarvegur",
            from_date=date(2026, 7, 31),
        )


def test_ambiguous_street_with_valid_area(
    calendar: GreenCalendar,
) -> None:
    result = calendar.next_collection_for_street(
        "Oyggjarvegur",
        area=4,
        from_date=date(2026, 7, 31),
    )

    assert result is not None
    assert result.area == 4
    assert result.collection_date == date(
        2026,
        8,
        18,
    )


def test_street_rejects_wrong_area(
    calendar: GreenCalendar,
) -> None:
    with pytest.raises(
        GreenCalendarError,
        match="is not registered",
    ):
        calendar.next_collection_for_street(
            "Hoyvíksvegur",
            area=4,
            from_date=date(2026, 7, 31),
        )


def test_unknown_area_raises_error(
    calendar: GreenCalendar,
) -> None:
    with pytest.raises(
        GreenCalendarError,
        match="Unknown area",
    ):
        calendar.next_collection(
            area=7,
            from_date=date(2026, 7, 31),
        )


def test_upcoming_collections_limit(
    calendar: GreenCalendar,
) -> None:
    results = calendar.upcoming_collections(
        area=3,
        from_date=date(2026, 7, 31),
        limit=2,
    )

    assert len(results) == 2

    assert results[0].collection_date == date(
        2026,
        8,
        11,
    )

    assert results[1].collection_date == date(
        2026,
        9,
        22,
    )


def test_bag_delivery_months(
    calendar: GreenCalendar,
) -> None:
    assert calendar.grey_bag_months() == (
        4,
        10,
    )

    assert calendar.red_bag_months() == (
        4,
        10,
    )


@pytest.mark.parametrize(
    ("settlement_name", "expected_name", "expected_area"),
    [
        ("Argir", "Argir", 6),
        ("Argjum", "Argir", 6),
        ("á Argjum", "Argir", 6),
        ("Kirkjubøur", "Kirkjubøur", 6),
        ("Kirkjubø", "Kirkjubøur", 6),
        ("í Kirkjubø", "Kirkjubøur", 6),
        ("Kollafjørður", "Kollafjørður", 1),
        ("Kollafirði", "Kollafjørður", 1),
        ("í Kollafirði", "Kollafjørður", 1),
    ],
)
def test_find_settlement_aliases(
    calendar: GreenCalendar,
    settlement_name: str,
    expected_name: str,
    expected_area: int,
) -> None:
    match = calendar.find_settlement(
        settlement_name
    )

    assert match is not None
    assert match.settlement == expected_name
    assert match.area == expected_area


def test_unknown_settlement_returns_none(
    calendar: GreenCalendar,
) -> None:
    assert (
        calendar.find_settlement(
            "Hetta staðarnavnið finst ikki"
        )
        is None
    )


def test_area_for_settlement(
    calendar: GreenCalendar,
) -> None:
    assert calendar.area_for_settlement(
        "Kirkjubø"
    ) == 6

    assert calendar.area_for_settlement(
        "Kollafirði"
    ) == 1


def test_unknown_settlement_raises_error(
    calendar: GreenCalendar,
) -> None:
    with pytest.raises(
        GreenCalendarError,
        match="Settlement not found",
    ):
        calendar.area_for_settlement(
            "Ókent stað"
        )


def test_settlements_for_area_1(
    calendar: GreenCalendar,
) -> None:
    settlements = calendar.settlements_for_area(1)

    assert settlements == (
        "Kaldbaksbotnur",
        "Kaldbak",
        "Kollafjørður",
        "Langasandur",
        "Oyrareingir",
        "Hvítanes",
        "Signabøur",
    )


def test_settlements_for_area_6(
    calendar: GreenCalendar,
) -> None:
    settlements = calendar.settlements_for_area(6)

    assert settlements == (
        "Argir",
        "Kirkjubøur",
        "Norðadalur",
        "Syðradalur",
        "Velbastaður",
    )


def test_address_uses_settlement_when_street_is_unknown(
    calendar: GreenCalendar,
) -> None:
    result = calendar.next_collection_for_address(
        street_name="Reynstún",
        settlement_name="Argjum",
        from_date=date(2026, 7, 31),
    )

    assert result is not None
    assert result.area == 6
    assert result.collection_date >= date(
        2026,
        7,
        31,
    )


def test_unknown_street_requires_settlement(
    calendar: GreenCalendar,
) -> None:
    with pytest.raises(
        GreenCalendarError,
        match="A settlement is required",
    ):
        calendar.next_collection_for_address(
            street_name="Reynstún",
            from_date=date(2026, 7, 31),
        )


def test_address_rejects_unknown_settlement(
    calendar: GreenCalendar,
) -> None:
    with pytest.raises(
        GreenCalendarError,
        match="Settlement not found",
    ):
        calendar.next_collection_for_address(
            street_name="Reynstún",
            settlement_name="Ókent stað",
            from_date=date(2026, 7, 31),
        )


def test_address_prefers_known_street(
    calendar: GreenCalendar,
) -> None:
    result = calendar.next_collection_for_address(
        street_name="Hoyvíksvegur",
        settlement_name="Argir",
        from_date=date(2026, 7, 31),
    )

    assert result is not None
    assert result.area == 3
    assert result.collection_date == date(
        2026,
        8,
        11,
    )