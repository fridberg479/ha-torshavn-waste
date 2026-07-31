"""Calendar for the Tórshavn Waste integration."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEvent,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TorshavnWasteConfigEntry
from .const import DOMAIN
from .coordinator import TorshavnWasteCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TorshavnWasteConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Tórshavn Waste calendar."""

    async_add_entities(
        [
            TorshavnWasteCalendar(
                coordinator=entry.runtime_data,
                entry=entry,
            )
        ]
    )


class TorshavnWasteCalendar(
    CoordinatorEntity[TorshavnWasteCoordinator],
    CalendarEntity,
):
    """Calendar containing waste collection events."""

    _attr_has_entity_name = True
    _attr_translation_key = "waste_collection"
    _attr_icon = "mdi:calendar-trash"

    def __init__(
        self,
        coordinator: TorshavnWasteCoordinator,
        entry: TorshavnWasteConfigEntry,
    ) -> None:
        """Initialize the waste collection calendar."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{entry.entry_id}_waste_collection_calendar"
        )

        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    entry.entry_id,
                )
            },
            name=entry.title,
            manufacturer="Kommunala Brennistøðin",
            model="Ruskinnsavning",
            configuration_url="https://www.kob.fo/",
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming waste collection event."""

        events: list[CalendarEvent] = []

        green_collection = (
            self.coordinator.data.next_green_collection
        )

        if green_collection is not None:
            events.append(
                self._green_event(
                    green_collection.collection_date
                )
            )

        general_collection = (
            self.coordinator.data
            .next_general_waste_collection
        )

        if general_collection is not None:
            events.append(
                self._general_event(
                    general_collection.collection_date
                )
            )

        if not events:
            return None

        return min(
            events,
            key=lambda event: event.start,
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return waste collection events in a time range."""

        range_start = start_date.date()
        range_end = end_date.date()

        events: list[CalendarEvent] = []

        for collection_date in (
            self.coordinator.calendar
            .collection_dates_for_area(
                self.coordinator.data.area
            )
        ):
            if not self._date_in_range(
                collection_date,
                range_start,
                range_end,
            ):
                continue

            events.append(
                self._green_event(collection_date)
            )

        general_area = (
            self.coordinator.data.general_waste_area
        )

        if general_area is not None:
            events.extend(
                self._general_events_in_range(
                    weekday=general_area.weekday,
                    range_start=range_start,
                    range_end=range_end,
                )
            )

        events.sort(
            key=lambda event: event.start
        )

        return events

    def _general_events_in_range(
        self,
        weekday: int,
        range_start: date,
        range_end: date,
    ) -> list[CalendarEvent]:
        """Return regular weekly general-waste events."""

        target_weekday = weekday - 1

        days_to_first = (
            target_weekday - range_start.weekday()
        ) % 7

        current_date = (
            range_start
            + timedelta(days=days_to_first)
        )

        events: list[CalendarEvent] = []

        while current_date < range_end:
            events.append(
                self._general_event(current_date)
            )

            current_date += timedelta(days=7)

        return events

    def _green_event(
        self,
        collection_date: date,
    ) -> CalendarEvent:
        """Create one green-bin collection event."""

        return CalendarEvent(
            summary="Green-bin collection",
            start=collection_date,
            end=collection_date + timedelta(days=1),
            description=(
                "Collection of the green bin. "
                f"Green-calendar area: "
                f"{self.coordinator.data.area}."
            ),
        )

    def _general_event(
        self,
        collection_date: date,
    ) -> CalendarEvent:
        """Create one regular general-waste event."""

        area = self.coordinator.data.general_waste_area

        details: list[str] = [
            "Regular general-waste collection.",
            (
                "Holiday-related schedule changes "
                "are not included."
            ),
        ]

        if area is not None:
            if area.weekday_name:
                details.append(
                    f"Regular weekday: {area.weekday_name}."
                )

            if area.route_id is not None:
                details.append(
                    f"Route: {area.route_id}."
                )

        return CalendarEvent(
            summary="General waste collection",
            start=collection_date,
            end=collection_date + timedelta(days=1),
            description=" ".join(details),
        )

    @staticmethod
    def _date_in_range(
        collection_date: date,
        range_start: date,
        range_end: date,
    ) -> bool:
        """Return whether an all-day event overlaps the range."""

        event_end = (
            collection_date
            + timedelta(days=1)
        )

        return (
            event_end > range_start
            and collection_date < range_end
        )