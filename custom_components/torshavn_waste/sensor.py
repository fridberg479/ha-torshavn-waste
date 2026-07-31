"""Sensors for the Tórshavn Waste integration."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TorshavnWasteConfigEntry
from .const import DOMAIN
from .coordinator import (
    TorshavnWasteCoordinator,
    TorshavnWasteData,
)

PARALLEL_UPDATES = 0


NEXT_GREEN_COLLECTION_DESCRIPTION = SensorEntityDescription(
    key="next_green_collection",
    translation_key="next_green_collection",
    device_class=SensorDeviceClass.DATE,
    icon="mdi:recycle",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TorshavnWasteConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Tórshavn Waste sensors from a config entry."""

    coordinator = entry.runtime_data

    async_add_entities(
        [
            TorshavnWasteNextGreenCollectionSensor(
                coordinator=coordinator,
                entry=entry,
                description=NEXT_GREEN_COLLECTION_DESCRIPTION,
            )
        ]
    )


class TorshavnWasteNextGreenCollectionSensor(
    CoordinatorEntity[TorshavnWasteCoordinator],
    SensorEntity,
):
    """Sensor showing the next green-bin collection."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TorshavnWasteCoordinator,
        entry: TorshavnWasteConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the next green-bin collection sensor."""

        super().__init__(coordinator)

        self.entity_description = description

        self._attr_unique_id = (
            f"{entry.entry_id}_{description.key}"
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
            model="Grøni kalendarin",
            configuration_url="https://www.kob.fo/",
        )

    @property
    def native_value(self) -> date | None:
        """Return the next green-bin collection date."""

        next_collection = (
            self.coordinator.data.next_green_collection
        )

        if next_collection is None:
            return None

        return next_collection.collection_date

    @property
    def extra_state_attributes(
        self,
    ) -> dict[str, Any]:
        """Return additional collection information."""

        data: TorshavnWasteData = self.coordinator.data
        next_collection = data.next_green_collection

        attributes: dict[str, Any] = {
            "street": data.street,
            "settlement": data.settlement,
            "area": data.area,
            "calendar_year": data.calendar_year,
            "grey_bag_months": list(
                data.grey_bag_months
            ),
            "red_bag_months": list(
                data.red_bag_months
            ),
            "upcoming_collections": [
                result.collection_date.isoformat()
                for result
                in data.upcoming_green_collections
            ],
        }

        if next_collection is not None:
            attributes["days_until"] = (
                next_collection.days_until
            )
        else:
            attributes["days_until"] = None

        return attributes