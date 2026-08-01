"""Tests for Faroese date formatting helpers."""

from __future__ import annotations

from datetime import date
import importlib.util
from pathlib import Path
import sys

import pytest


MODULE_FILE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "torshavn_waste"
    / "formatting.py"
)

spec = importlib.util.spec_from_file_location(
    "torshavn_waste_formatting",
    MODULE_FILE,
)

if spec is None or spec.loader is None:
    raise RuntimeError(
        f"Could not load formatting module from {MODULE_FILE}"
    )

formatting_module = importlib.util.module_from_spec(
    spec
)
sys.modules[spec.name] = formatting_module
spec.loader.exec_module(formatting_module)

format_date_fo = formatting_module.format_date_fo
format_month_fo = formatting_module.format_month_fo
month_name_fo = formatting_module.month_name_fo
relative_days_fo = formatting_module.relative_days_fo
weekday_name_fo = formatting_module.weekday_name_fo


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (date(2026, 8, 3), "mánadagur"),
        (date(2026, 8, 4), "týsdagur"),
        (date(2026, 8, 5), "mikudagur"),
        (date(2026, 8, 6), "hósdagur"),
        (date(2026, 8, 7), "fríggjadagur"),
        (date(2026, 8, 8), "leygardagur"),
        (date(2026, 8, 9), "sunnudagur"),
    ],
)
def test_weekday_name_fo(
    value: date,
    expected: str,
) -> None:
    """Weekday names are formatted correctly."""

    assert weekday_name_fo(value) == expected


@pytest.mark.parametrize(
    ("month", "expected"),
    [
        (1, "januar"),
        (2, "februar"),
        (3, "mars"),
        (4, "apríl"),
        (5, "mai"),
        (6, "juni"),
        (7, "juli"),
        (8, "august"),
        (9, "september"),
        (10, "oktober"),
        (11, "november"),
        (12, "desember"),
    ],
)
def test_month_name_fo(
    month: int,
    expected: str,
) -> None:
    """Month names are formatted correctly."""

    assert month_name_fo(month) == expected


@pytest.mark.parametrize(
    "month",
    [
        0,
        13,
    ],
)
def test_month_name_rejects_invalid_month(
    month: int,
) -> None:
    """Invalid month numbers are rejected."""

    with pytest.raises(
        ValueError,
        match="between 1 and 12",
    ):
        month_name_fo(month)


def test_format_date_fo() -> None:
    """A complete Faroese date is formatted correctly."""

    assert format_date_fo(
        date(2026, 8, 6)
    ) == "hósdagur 6. august 2026"


def test_format_month_fo() -> None:
    """A month and year are formatted correctly."""

    assert format_month_fo(
        2026,
        10,
    ) == "oktober 2026"


@pytest.mark.parametrize(
    ("days_until", "expected"),
    [
        (0, "í dag"),
        (1, "í morgin"),
        (2, "um 2 dagar"),
        (31, "um 31 dagar"),
    ],
)
def test_relative_days_fo(
    days_until: int,
    expected: str,
) -> None:
    """Relative-day text is formatted correctly."""

    assert relative_days_fo(
        days_until
    ) == expected


def test_relative_days_rejects_negative_value() -> None:
    """Negative day values are rejected."""

    with pytest.raises(
        ValueError,
        match="cannot be negative",
    ):
        relative_days_fo(-1)