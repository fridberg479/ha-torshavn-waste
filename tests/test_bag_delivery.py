"""Tests for bag-delivery calculations."""

from __future__ import annotations

from datetime import date
import importlib.util
from pathlib import Path
import sys


MODULE_FILE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "torshavn_waste"
    / "bag_delivery.py"
)

spec = importlib.util.spec_from_file_location(
    "torshavn_waste_bag_delivery",
    MODULE_FILE,
)

if spec is None or spec.loader is None:
    raise RuntimeError(
        f"Could not load bag-delivery module from {MODULE_FILE}"
    )

bag_delivery_module = importlib.util.module_from_spec(
    spec
)
sys.modules[spec.name] = bag_delivery_module
spec.loader.exec_module(bag_delivery_module)

BagDeliveryResult = (
    bag_delivery_module.BagDeliveryResult
)
next_bag_delivery = (
    bag_delivery_module.next_bag_delivery
)


def test_next_delivery_is_october() -> None:
    """October is returned after the April delivery."""

    result = next_bag_delivery(
        calendar_year=2026,
        red_bag_months=(4, 10),
        grey_bag_months=(4, 10),
        from_date=date(2026, 8, 1),
    )

    assert isinstance(result, BagDeliveryResult)
    assert result.delivery_year == 2026
    assert result.delivery_month == 10
    assert result.months_until == 2
    assert result.bag_types == (
        "red",
        "grey",
    )


def test_delivery_in_current_month_is_included() -> None:
    """A delivery in the current month is still returned."""

    result = next_bag_delivery(
        calendar_year=2026,
        red_bag_months=(4, 10),
        grey_bag_months=(4, 10),
        from_date=date(2026, 10, 15),
    )

    assert result is not None
    assert result.delivery_month == 10
    assert result.months_until == 0
    assert result.bag_types == (
        "red",
        "grey",
    )


def test_first_delivery_is_returned_before_calendar_year() -> None:
    """The first delivery is returned for an earlier year."""

    result = next_bag_delivery(
        calendar_year=2026,
        red_bag_months=(4, 10),
        grey_bag_months=(4, 10),
        from_date=date(2025, 12, 31),
    )

    assert result is not None
    assert result.delivery_year == 2026
    assert result.delivery_month == 4
    assert result.months_until == 4


def test_no_delivery_after_last_delivery_month() -> None:
    """No delivery is returned after the final delivery month."""

    result = next_bag_delivery(
        calendar_year=2026,
        red_bag_months=(4, 10),
        grey_bag_months=(4, 10),
        from_date=date(2026, 11, 1),
    )

    assert result is None


def test_no_delivery_after_calendar_year() -> None:
    """No delivery is returned after the calendar year."""

    result = next_bag_delivery(
        calendar_year=2026,
        red_bag_months=(4, 10),
        grey_bag_months=(4, 10),
        from_date=date(2027, 1, 1),
    )

    assert result is None


def test_bag_types_can_have_different_months() -> None:
    """Red and grey bags do not have to share delivery months."""

    result = next_bag_delivery(
        calendar_year=2026,
        red_bag_months=(4, 10),
        grey_bag_months=(6, 10),
        from_date=date(2026, 5, 1),
    )

    assert result is not None
    assert result.delivery_month == 6
    assert result.months_until == 1
    assert result.bag_types == ("grey",)


def test_empty_delivery_lists_return_none() -> None:
    """Empty delivery lists return no result."""

    result = next_bag_delivery(
        calendar_year=2026,
        red_bag_months=(),
        grey_bag_months=(),
        from_date=date(2026, 1, 1),
    )

    assert result is None