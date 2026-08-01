"""Bag-delivery helpers for the Tórshavn Waste integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class BagDeliveryResult:
    """Information about an upcoming bag delivery."""

    delivery_year: int
    delivery_month: int
    months_until: int
    bag_types: tuple[str, ...]


def next_bag_delivery(
    *,
    calendar_year: int,
    red_bag_months: tuple[int, ...],
    grey_bag_months: tuple[int, ...],
    from_date: date,
) -> BagDeliveryResult | None:
    """Return the next red or grey bag-delivery month.

    The source calendar only specifies a month, not an exact date.
    A delivery in the current month is therefore still considered
    upcoming.
    """

    if from_date.year > calendar_year:
        return None

    reference_month = (
        from_date.month
        if from_date.year == calendar_year
        else 1
    )

    delivery_months = sorted(
        set(red_bag_months)
        | set(grey_bag_months)
    )

    for month in delivery_months:
        if month < reference_month:
            continue

        bag_types: list[str] = []

        if month in red_bag_months:
            bag_types.append("red")

        if month in grey_bag_months:
            bag_types.append("grey")

        months_until = (
            (calendar_year - from_date.year) * 12
            + month
            - from_date.month
        )

        return BagDeliveryResult(
            delivery_year=calendar_year,
            delivery_month=month,
            months_until=months_until,
            bag_types=tuple(bag_types),
        )

    return None