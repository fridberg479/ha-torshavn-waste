"""Tests for holiday helpers."""

from __future__ import annotations

from datetime import date
import importlib.util
from pathlib import Path
import sys


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "torshavn_waste"
    / "holidays.py"
)

SPEC = importlib.util.spec_from_file_location(
    "torshavn_waste_holidays",
    MODULE_PATH,
)

assert SPEC is not None
assert SPEC.loader is not None

holidays = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = holidays
SPEC.loader.exec_module(holidays)


def test_load_holidays() -> None:
    """The holiday file can be loaded."""
    loaded_holidays = holidays.load_holidays()

    assert loaded_holidays
    assert date(2026, 12, 24) in loaded_holidays


def test_get_single_holiday_name() -> None:
    """A date with one holiday returns the correct name."""
    assert holidays.get_holiday_name(date(2026, 12, 24)) == "Jólaftan"


def test_get_multiple_holiday_names() -> None:
    """A date with multiple holiday names returns all names."""
    assert holidays.get_holiday_names(date(2028, 6, 5)) == [
        "2. Hvítusunnudagur",
        "Grundlógardagur",
    ]

    assert holidays.get_holiday_name(date(2028, 6, 5)) == (
        "2. Hvítusunnudagur, Grundlógardagur"
    )


def test_unknown_date_is_not_holiday() -> None:
    """A date not in the file is not treated as a holiday."""
    value = date(2026, 8, 1)

    assert holidays.get_holiday_names(value) == []
    assert holidays.get_holiday_name(value) is None
    assert holidays.is_holiday(value) is False


def test_known_date_is_holiday() -> None:
    """A date in the file is treated as a holiday."""
    assert holidays.is_holiday(date(2027, 3, 25)) is True