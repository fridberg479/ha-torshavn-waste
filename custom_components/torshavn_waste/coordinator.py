"""Data coordinator for the Tórshavn Waste integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
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
from .const import (
    CONF_AREA,
    CONF_SETTLEMENT,
    CONF_STREET,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(hours=6)


@dataclass(frozen=True, slots=True)
class TorshavnWasteData:
    """Runtime data calculated for one configured address."""

    street: str
    settlement: str | None
    area: int
    calendar_year: int
    next_green_collection: CollectionResult | None
    upcoming_green_collections: tuple[CollectionResult, ...]
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
            street_match = self.calendar.find_street(
                self.street
            )

            canonical_street = self.street
            canonical_settlement: str | None = None

            if street_match is not None:
                canonical_street = street_match.street

                if self.area not in street_match.areas:
                    raise GreenCalendarError(
                        f"Street '{street_match.street}' "
                        f"is not registered in area {self.area}."
                    )

            else:
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

                canonical_settlement = (
                    settlement_match.settlement
                )

            next_collection = (
                self.calendar.next_collection(
                    area=self.area,
                    from_date=today,
                    include_today=True,
                )
            )

            upcoming_collections = (
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
                "Could not update waste collection data: "
                f"{error}"
            ) from error

        return TorshavnWasteData(
            street=canonical_street,
            settlement=canonical_settlement,
            area=self.area,
            calendar_year=self.calendar.year,
            next_green_collection=next_collection,
            upcoming_green_collections=(
                upcoming_collections
            ),
            grey_bag_months=grey_bag_months,
            red_bag_months=red_bag_months,
        )