from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


DEFAULT_DATA_FILE = (
    Path(__file__).resolve().parent
    / "data"
    / "green_calendar_2026.json"
)

class GreenCalendarError(Exception):
    """Base error for green-calendar operations."""


class GreenCalendarDataError(GreenCalendarError):
    """Raised when the calendar data is missing or invalid."""


@dataclass(frozen=True, slots=True)
class StreetMatch:
    """One matched street and its possible collection areas."""

    street: str
    areas: tuple[int, ...]

    @property
    def is_ambiguous(self) -> bool:
        """Return True when the street belongs to multiple areas."""

        return len(self.areas) > 1


@dataclass(frozen=True, slots=True)
class SettlementMatch:
    """One matched settlement and its collection area."""

    settlement: str
    area: int


@dataclass(frozen=True, slots=True)
class CollectionResult:
    """Information about a green-bin collection."""

    area: int
    collection_date: date
    days_until: int


def normalize_street_name(value: str) -> str:
    """
    Normalize a street name for comparison.

    Keeps Faroese letters, but ignores:
    - upper/lower case
    - repeated whitespace
    - leading/trailing whitespace
    - full stops and commas
    """

    value = unicodedata.normalize("NFC", value)
    value = value.casefold()
    value = value.replace(".", " ")
    value = value.replace(",", " ")
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_settlement_name(value: str) -> str:
    """
    Normalize a settlement name for comparison.

    Common Faroese prepositions are ignored so values such as
    "á Argjum" and "í Kirkjubø" can be matched safely.
    """

    value = normalize_street_name(value)

    for prefix in ("í ", "á ", "úr ", "við "):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break

    return value.strip()


class GreenCalendar:
    """Read and query KOB green-calendar data."""

    def __init__(
        self,
        data_file: Path | str = DEFAULT_DATA_FILE,
    ) -> None:
        self._data_file = Path(data_file)
        self._data: dict[str, Any] = {}

        self._year: int = 0
        self._streets_by_area: dict[int, tuple[str, ...]] = {}
        self._settlements_by_area: dict[int, tuple[str, ...]] = {}
        self._dates_by_area: dict[int, tuple[date, ...]] = {}

        self._street_index: dict[str, StreetMatch] = {}
        self._settlement_index: dict[str, SettlementMatch] = {}

        self._load()

    @property
    def year(self) -> int:
        """Return the calendar year."""

        return self._year

    @property
    def data_file(self) -> Path:
        """Return the path to the loaded JSON file."""

        return self._data_file

    @property
    def areas(self) -> tuple[int, ...]:
        """Return available collection areas."""

        return tuple(sorted(self._dates_by_area))

    def _load(self) -> None:
        """Load and index the JSON data."""

        if not self._data_file.is_file():
            raise GreenCalendarDataError(
                f"Calendar data file not found: {self._data_file}"
            )

        try:
            content = self._data_file.read_text(
                encoding="utf-8"
            )
        except OSError as error:
            raise GreenCalendarDataError(
                f"Could not read calendar data: {error}"
            ) from error

        try:
            data = json.loads(content)
        except json.JSONDecodeError as error:
            raise GreenCalendarDataError(
                "Invalid JSON in calendar data: "
                f"line {error.lineno}, column {error.colno}: "
                f"{error.msg}"
            ) from error

        if not isinstance(data, dict):
            raise GreenCalendarDataError(
                "Calendar data must contain a JSON object."
            )

        year = data.get("year")

        if not isinstance(year, int):
            raise GreenCalendarDataError(
                "Calendar year is missing or invalid."
            )

        areas = data.get("areas")

        if not isinstance(areas, dict):
            raise GreenCalendarDataError(
                "Calendar areas are missing or invalid."
            )

        streets_by_area: dict[int, tuple[str, ...]] = {}
        settlements_by_area: dict[int, tuple[str, ...]] = {}
        dates_by_area: dict[int, tuple[date, ...]] = {}

        street_locations: dict[str, set[int]] = {}
        settlement_locations: dict[str, int] = {}
        settlement_display_names: dict[str, str] = {}
        display_names: dict[str, str] = {}

        for area_number in range(1, 7):
            area_data = areas.get(str(area_number))

            if not isinstance(area_data, dict):
                raise GreenCalendarDataError(
                    f"Area {area_number} is missing or invalid."
                )

            raw_streets = area_data.get("streets")
            raw_settlements = area_data.get("settlements", [])
            raw_dates = area_data.get("collection_dates")

            if not isinstance(raw_streets, list):
                raise GreenCalendarDataError(
                    f"Street list for area {area_number} is invalid."
                )

            if not isinstance(raw_settlements, list):
                raise GreenCalendarDataError(
                    f"Settlement list for area {area_number} is invalid."
                )

            if not isinstance(raw_dates, list):
                raise GreenCalendarDataError(
                    f"Collection dates for area {area_number} are invalid."
                )

            streets: list[str] = []

            for value in raw_streets:
                if not isinstance(value, str) or not value.strip():
                    raise GreenCalendarDataError(
                        "Invalid street in area "
                        f"{area_number}: {value!r}"
                    )

                street = value.strip()
                streets.append(street)

                key = normalize_street_name(street)

                street_locations.setdefault(
                    key,
                    set(),
                ).add(area_number)

                display_names.setdefault(
                    key,
                    street,
                )

            settlements: list[str] = []

            for value in raw_settlements:
                if not isinstance(value, str) or not value.strip():
                    raise GreenCalendarDataError(
                        "Invalid settlement in area "
                        f"{area_number}: {value!r}"
                    )

                settlement = value.strip()
                key = normalize_settlement_name(settlement)

                if key in settlement_locations:
                    raise GreenCalendarDataError(
                        f"Settlement '{settlement}' is registered "
                        "in more than one area."
                    )

                settlements.append(settlement)
                settlement_locations[key] = area_number
                settlement_display_names[key] = settlement

            collection_dates: list[date] = []

            for value in raw_dates:
                if not isinstance(value, str):
                    raise GreenCalendarDataError(
                        "Invalid collection date in area "
                        f"{area_number}: {value!r}"
                    )

                try:
                    parsed_date = date.fromisoformat(value)
                except ValueError as error:
                    raise GreenCalendarDataError(
                        "Invalid collection date in area "
                        f"{area_number}: {value}"
                    ) from error

                if parsed_date.year != year:
                    raise GreenCalendarDataError(
                        f"Collection date {value} does not "
                        f"belong to {year}."
                    )

                collection_dates.append(parsed_date)

            streets_by_area[area_number] = tuple(streets)
            settlements_by_area[area_number] = tuple(settlements)
            dates_by_area[area_number] = tuple(
                sorted(collection_dates)
            )

        street_index: dict[str, StreetMatch] = {}

        for key, area_numbers in street_locations.items():
            street_index[key] = StreetMatch(
                street=display_names[key],
                areas=tuple(sorted(area_numbers)),
            )

        raw_aliases = data.get("settlement_aliases", {})

        if not isinstance(raw_aliases, dict):
            raise GreenCalendarDataError(
                "settlement_aliases is invalid."
            )

        settlement_index: dict[str, SettlementMatch] = {}

        for key, area_number in settlement_locations.items():
            settlement_index[key] = SettlementMatch(
                settlement=settlement_display_names[key],
                area=area_number,
            )

        for alias, canonical_name in raw_aliases.items():
            if (
                not isinstance(alias, str)
                or not isinstance(canonical_name, str)
            ):
                raise GreenCalendarDataError(
                    "Invalid settlement alias."
                )

            canonical_key = normalize_settlement_name(
                canonical_name
            )
            canonical_match = settlement_index.get(canonical_key)

            if canonical_match is None:
                raise GreenCalendarDataError(
                    "Settlement alias points to an unknown "
                    f"settlement: {canonical_name}"
                )

            alias_key = normalize_settlement_name(alias)
            settlement_index[alias_key] = canonical_match

        self._data = data
        self._year = year
        self._streets_by_area = streets_by_area
        self._settlements_by_area = settlements_by_area
        self._dates_by_area = dates_by_area
        self._street_index = street_index
        self._settlement_index = settlement_index

    def reload(self) -> None:
        """Reload calendar data from disk."""

        self._load()

    def find_street(
        self,
        street_name: str,
    ) -> StreetMatch | None:
        """
        Find an exact normalized street match.

        Returns None when the street is not found.
        """

        key = normalize_street_name(street_name)

        if not key:
            return None

        return self._street_index.get(key)

    def search_streets(
        self,
        query: str,
        limit: int = 10,
    ) -> list[StreetMatch]:
        """
        Search street names using a normalized substring match.

        Exact matches are returned first.
        """

        normalized_query = normalize_street_name(query)

        if not normalized_query:
            return []

        exact = self._street_index.get(normalized_query)

        matches: list[
            tuple[int, str, StreetMatch]
        ] = []

        for key, match in self._street_index.items():
            if key == normalized_query:
                continue

            if normalized_query not in key:
                continue

            starts_with_query = key.startswith(
                normalized_query
            )

            priority = 0 if starts_with_query else 1

            matches.append(
                (
                    priority,
                    match.street.casefold(),
                    match,
                )
            )

        matches.sort(
            key=lambda item: (
                item[0],
                item[1],
            )
        )

        result: list[StreetMatch] = []

        if exact is not None:
            result.append(exact)

        result.extend(
            item[2]
            for item in matches
        )

        return result[:limit]

    def find_settlement(
        self,
        settlement_name: str,
    ) -> SettlementMatch | None:
        """
        Find a settlement using its official name or a known alias.

        Returns None when the settlement is not found.
        """

        key = normalize_settlement_name(settlement_name)

        if not key:
            return None

        return self._settlement_index.get(key)

    def area_for_settlement(
        self,
        settlement_name: str,
    ) -> int:
        """Return the collection area for a settlement."""

        match = self.find_settlement(settlement_name)

        if match is None:
            raise GreenCalendarError(
                f"Settlement not found: {settlement_name}"
            )

        return match.area

    def settlements_for_area(
        self,
        area: int,
    ) -> tuple[str, ...]:
        """Return all settlements registered for an area."""

        self._require_area(area)

        return self._settlements_by_area[area]

    def streets_for_area(
        self,
        area: int,
    ) -> tuple[str, ...]:
        """Return all streets registered for an area."""

        self._require_area(area)

        return self._streets_by_area[area]

    def collection_dates_for_area(
        self,
        area: int,
    ) -> tuple[date, ...]:
        """Return all collection dates for an area."""

        self._require_area(area)

        return self._dates_by_area[area]

    def next_collection(
        self,
        area: int,
        from_date: date | None = None,
        include_today: bool = True,
    ) -> CollectionResult | None:
        """
        Return the next green-bin collection for an area.

        Returns None when no later collection exists in the
        loaded calendar year.
        """

        self._require_area(area)

        reference_date = from_date or date.today()

        for collection_date in self._dates_by_area[area]:
            if include_today:
                is_match = collection_date >= reference_date
            else:
                is_match = collection_date > reference_date

            if not is_match:
                continue

            return CollectionResult(
                area=area,
                collection_date=collection_date,
                days_until=(
                    collection_date - reference_date
                ).days,
            )

        return None

    def upcoming_collections(
        self,
        area: int,
        from_date: date | None = None,
        limit: int | None = None,
        include_today: bool = True,
    ) -> tuple[CollectionResult, ...]:
        """Return upcoming collections for an area."""

        self._require_area(area)

        reference_date = from_date or date.today()
        results: list[CollectionResult] = []

        for collection_date in self._dates_by_area[area]:
            if include_today:
                is_match = collection_date >= reference_date
            else:
                is_match = collection_date > reference_date

            if not is_match:
                continue

            results.append(
                CollectionResult(
                    area=area,
                    collection_date=collection_date,
                    days_until=(
                        collection_date - reference_date
                    ).days,
                )
            )

            if limit is not None and len(results) >= limit:
                break

        return tuple(results)

    def next_collection_for_street(
        self,
        street_name: str,
        area: int | None = None,
        from_date: date | None = None,
        include_today: bool = True,
    ) -> CollectionResult | None:
        """
        Return the next collection for a street.

        When the street belongs to multiple areas, the caller must
        provide an area.
        """

        match = self.find_street(street_name)

        if match is None:
            raise GreenCalendarError(
                f"Street not found: {street_name}"
            )

        selected_area = area

        if selected_area is None:
            if match.is_ambiguous:
                areas = ", ".join(
                    str(value)
                    for value in match.areas
                )

                raise GreenCalendarError(
                    f"Street '{match.street}' belongs to "
                    f"multiple areas: {areas}"
                )

            selected_area = match.areas[0]

        if selected_area not in match.areas:
            raise GreenCalendarError(
                f"Street '{match.street}' is not registered "
                f"in area {selected_area}."
            )

        return self.next_collection(
            area=selected_area,
            from_date=from_date,
            include_today=include_today,
        )

    def next_collection_for_address(
        self,
        street_name: str,
        settlement_name: str | None = None,
        area: int | None = None,
        from_date: date | None = None,
        include_today: bool = True,
    ) -> CollectionResult | None:
        """
        Return the next collection for an address.

        The street list is checked first. When the street is not
        listed, a settlement must be provided.
        """

        street_match = self.find_street(street_name)

        if street_match is not None:
            return self.next_collection_for_street(
                street_name=street_name,
                area=area,
                from_date=from_date,
                include_today=include_today,
            )

        if settlement_name is None:
            raise GreenCalendarError(
                f"Street not found: {street_name}. "
                "A settlement is required."
            )

        settlement_match = self.find_settlement(
            settlement_name
        )

        if settlement_match is None:
            raise GreenCalendarError(
                f"Settlement not found: {settlement_name}"
            )

        if area is not None and area != settlement_match.area:
            raise GreenCalendarError(
                f"Settlement '{settlement_match.settlement}' "
                f"belongs to area {settlement_match.area}, "
                f"not area {area}."
            )

        return self.next_collection(
            area=settlement_match.area,
            from_date=from_date,
            include_today=include_today,
        )

    def grey_bag_months(self) -> tuple[int, ...]:
        """Return months when grey bags are delivered."""

        return self._bag_months("grey_bags")

    def red_bag_months(self) -> tuple[int, ...]:
        """Return months when red bags are delivered."""

        return self._bag_months("red_bag")

    def bag_description(
        self,
        bag_type: str,
    ) -> str:
        """Return the description for one bag-delivery type."""

        deliveries = self._data.get(
            "bag_deliveries"
        )

        if not isinstance(deliveries, dict):
            raise GreenCalendarDataError(
                "bag_deliveries is missing."
            )

        section = deliveries.get(bag_type)

        if not isinstance(section, dict):
            raise GreenCalendarDataError(
                f"Unknown bag type: {bag_type}"
            )

        description = section.get("description")

        if not isinstance(description, str):
            raise GreenCalendarDataError(
                f"Description for {bag_type} is invalid."
            )

        return description

    def _bag_months(
        self,
        bag_type: str,
    ) -> tuple[int, ...]:
        """Return delivery months for a bag type."""

        deliveries = self._data.get(
            "bag_deliveries"
        )

        if not isinstance(deliveries, dict):
            raise GreenCalendarDataError(
                "bag_deliveries is missing."
            )

        section = deliveries.get(bag_type)

        if not isinstance(section, dict):
            raise GreenCalendarDataError(
                f"Unknown bag type: {bag_type}"
            )

        months = section.get("months")

        if not isinstance(months, list):
            raise GreenCalendarDataError(
                f"Months for {bag_type} are invalid."
            )

        if not all(
            isinstance(month, int)
            for month in months
        ):
            raise GreenCalendarDataError(
                f"Months for {bag_type} are invalid."
            )

        return tuple(months)

    def _require_area(
        self,
        area: int,
    ) -> None:
        """Raise when an area does not exist."""

        if area not in self._dates_by_area:
            raise GreenCalendarError(
                f"Unknown area: {area}"
            )