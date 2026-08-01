"""Holiday helpers for the Tórshavn Waste integration."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Final


_HOLIDAY_FILE: Final = Path(__file__).parent / "data" / "holidays.json"


def load_holidays() -> dict[date, list[str]]:
    """Load holidays from holidays.json.

    Returns a dictionary where each date can contain one or more holiday names.
    """
    with _HOLIDAY_FILE.open(encoding="utf-8") as file:
        raw_data = json.load(file)

    holidays: dict[date, list[str]] = {}

    for item in raw_data.get("holidays", []):
        holiday_date = date.fromisoformat(item["date"])
        holiday_name = item["name"]

        holidays.setdefault(holiday_date, []).append(holiday_name)

    return holidays


HOLIDAYS: Final = load_holidays()


def get_holiday_names(value: date) -> list[str]:
    """Return all holiday names for a date."""
    return HOLIDAYS.get(value, [])


def get_holiday_name(value: date) -> str | None:
    """Return holiday names as one string, or None if it is not a holiday."""
    names = get_holiday_names(value)

    if not names:
        return None

    return ", ".join(names)


def is_holiday(value: date) -> bool:
    """Return True if the date is listed as a holiday."""
    return value in HOLIDAYS