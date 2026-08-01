"""Formatting helpers for the Tórshavn Waste integration."""

from __future__ import annotations

from datetime import date


WEEKDAY_NAMES_FO: tuple[str, ...] = (
    "mánadagur",
    "týsdagur",
    "mikudagur",
    "hósdagur",
    "fríggjadagur",
    "leygardagur",
    "sunnudagur",
)

MONTH_NAMES_FO: tuple[str, ...] = (
    "",
    "januar",
    "februar",
    "mars",
    "apríl",
    "mai",
    "juni",
    "juli",
    "august",
    "september",
    "oktober",
    "november",
    "desember",
)


def weekday_name_fo(value: date) -> str:
    """Return the Faroese weekday name for a date."""

    return WEEKDAY_NAMES_FO[value.weekday()]


def month_name_fo(month: int) -> str:
    """Return the Faroese name for a month number."""

    if month < 1 or month > 12:
        raise ValueError(
            f"Month must be between 1 and 12: {month}"
        )

    return MONTH_NAMES_FO[month]


def format_date_fo(value: date) -> str:
    """Return a readable Faroese date."""

    return (
        f"{weekday_name_fo(value)} "
        f"{value.day}. "
        f"{month_name_fo(value.month)} "
        f"{value.year}"
    )


def format_month_fo(
    year: int,
    month: int,
) -> str:
    """Return a readable Faroese month and year."""

    return f"{month_name_fo(month)} {year}"


def relative_days_fo(days_until: int) -> str:
    """Return a readable Faroese relative-day description."""

    if days_until < 0:
        raise ValueError(
            "days_until cannot be negative."
        )

    if days_until == 0:
        return "í dag"

    if days_until == 1:
        return "í morgin"

    return f"um {days_until} dagar"