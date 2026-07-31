"""Data coordinator for the Tórshavn Waste integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from functools import partial
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import (
    CollectionResult,
    GreenCalendar,
    GreenCalendarError,
)
from .arcgis import (
    ArcGISWasteError,
    GeneralWasteArea,
    fetch_general_waste_areas,
)
from .const import (
    CONF_AREA,
    CONF_SETTLEMENT,
    CONF_STREET,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(hours=6)


@dataclass(frozen=True, slots=True)
class GeneralWasteCollectionResult:
    """Information about the next general-waste collection."""

    collection_date: date
    days_until: int


@dataclass(frozen=True, slots=True)
class TorshavnWasteData:
    """Runtime data calculated for one configured address."""

    street: str
    settlement: str | None
    area: int
    calendar_year: int

    next_green_collection: CollectionResult | None
    upcoming_green_collections: tuple[CollectionResult, ...]

    general_waste_area: GeneralWasteArea | None
    next_general_waste_collection: (
        GeneralWasteCollectionResult | None
    )
    general_waste_error: str | None

    grey_bag_months: tuple[int, ...]
    red_bag_months: tuple[int, ...]


class TorshavnWasteCoordinator(
    DataUpdateCoordinator[TorshavnWasteData]
):
    """Coordinate waste collection data updates."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        calendar: GreenCalendar,
    ) -> None:
        """Initialize the coordinator."""

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

        self.config_entry = entry
        self.calendar = calendar

        self.street = str(
            entry.data[CONF_STREET]
        ).strip()

        raw_settlement = entry.data.get(
            CONF_SETTLEMENT
        )

        if raw_settlement is None:
            self.settlement: str | None = None
        else:
            settlement = str(raw_settlement).strip()
            self.settlement = settlement or None

        self.area = int(
            entry.data[CONF_AREA]
        )

    async def _async_update_data(
        self,
    ) -> TorshavnWasteData:
        """Calculate current waste collection information."""

        today = date.today()

        try:
            (
                canonical_street,
                canonical_settlement,
            ) = self._resolve_green_address()

            next_green_collection = (
                self.calendar.next_collection(
                    area=self.area,
                    from_date=today,
                    include_today=True,
                )
            )

            upcoming_green_collections = (
                self.calendar.upcoming_collections(
                    area=self.area,
                    from_date=today,
                    limit=5,
                    include_today=True,
                )
            )

            grey_bag_months = (
                self.calendar.grey_bag_months()
            )

            red_bag_months = (
                self.calendar.red_bag_months()
            )

        except GreenCalendarError as error:
            raise UpdateFailed(
                "Could not update green waste collection data: "
                f"{error}"
            ) from error

        (
            general_waste_area,
            next_general_waste_collection,
            general_waste_error,
        ) = await self._async_get_general_waste_data(
            today
        )

        return TorshavnWasteData(
            street=canonical_street,
            settlement=canonical_settlement,
            area=self.area,
            calendar_year=self.calendar.year,
            next_green_collection=next_green_collection,
            upcoming_green_collections=(
                upcoming_green_collections
            ),
            general_waste_area=general_waste_area,
            next_general_waste_collection=(
                next_general_waste_collection
            ),
            general_waste_error=general_waste_error,
            grey_bag_months=grey_bag_months,
            red_bag_months=red_bag_months,
        )

    def _resolve_green_address(
        self,
    ) -> tuple[str, str | None]:
        """Validate and canonicalize the green-calendar address."""

        street_match = self.calendar.find_street(
            self.street
        )

        if street_match is not None:
            if self.area not in street_match.areas:
                raise GreenCalendarError(
                    f"Street '{street_match.street}' "
                    f"is not registered in area {self.area}."
                )

            return street_match.street, None

        if self.settlement is None:
            raise GreenCalendarError(
                f"Street not found: {self.street}. "
                "A settlement is required."
            )

        settlement_match = (
            self.calendar.find_settlement(
                self.settlement
            )
        )

        if settlement_match is None:
            raise GreenCalendarError(
                "Settlement not found: "
                f"{self.settlement}"
            )

        if settlement_match.area != self.area:
            raise GreenCalendarError(
                f"Settlement "
                f"'{settlement_match.settlement}' "
                f"belongs to area "
                f"{settlement_match.area}, "
                f"not area {self.area}."
            )

        return (
            self.street,
            settlement_match.settlement,
        )

    async def _async_get_general_waste_data(
        self,
        today: date,
    ) -> tuple[
        GeneralWasteArea | None,
        GeneralWasteCollectionResult | None,
        str | None,
    ]:
        """Fetch and calculate general-waste collection data."""

        fetch_call = partial(
            fetch_general_waste_areas,
            latitude=self.hass.config.latitude,
            longitude=self.hass.config.longitude,
            radius_metres=25,
        )

        try:
            areas = await self.hass.async_add_executor_job(
                fetch_call
            )
        except ArcGISWasteError as error:
            _LOGGER.warning(
                "Could not fetch general waste data: %s",
                error,
            )

            return None, None, str(error)

        if not areas:
            error = (
                "No general waste collection area was found "
                "at the Home Assistant coordinates."
            )

            _LOGGER.warning(error)

            return None, None, error

        if len(areas) > 1:
            error = (
                "More than one general waste collection area "
                "was found at the Home Assistant coordinates."
            )

            _LOGGER.warning(error)

            return None, None, error

        general_waste_area = areas[0]

        next_collection = (
            self._next_general_waste_collection(
                weekday=general_waste_area.weekday,
                from_date=today,
            )
        )

        return (
            general_waste_area,
            next_collection,
            None,
        )

    @staticmethod
    def _next_general_waste_collection(
        weekday: int,
        from_date: date,
    ) -> GeneralWasteCollectionResult:
        """
        Calculate the next weekly general-waste collection.

        ArcGIS uses Monday=1 through Friday=5, while Python
        uses Monday=0 through Sunday=6.
        """

        target_weekday = weekday - 1

        days_until = (
            target_weekday - from_date.weekday()
        ) % 7

        collection_date = (
            from_date
            + timedelta(days=days_until)
        )

        return GeneralWasteCollectionResult(
            collection_date=collection_date,
            days_until=days_until,
        )