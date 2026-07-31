"""Binary sensors for the Tórshavn Waste integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
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


GREEN_COLLECTION_TOMORROW_DESCRIPTION = (
    BinarySensorEntityDescription(
        key="green_collection_tomorrow",
        translation_key="green_collection_tomorrow",
        icon="mdi:recycle",
    )
)

GENERAL_WASTE_COLLECTION_TOMORROW_DESCRIPTION = (
    BinarySensorEntityDescription(
        key="general_waste_collection_tomorrow",
        translation_key="general_waste_collection_tomorrow",
        icon="mdi:trash-can",
    )
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TorshavnWasteConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Tórshavn Waste binary sensors."""

    coordinator = entry.runtime_data

    async_add_entities(
        [
            TorshavnWasteGreenCollectionTomorrowBinarySensor(
                coordinator=coordinator,
                entry=entry,
                description=(
                    GREEN_COLLECTION_TOMORROW_DESCRIPTION
                ),
            ),
            TorshavnWasteGeneralWasteTomorrowBinarySensor(
                coordinator=coordinator,
                entry=entry,
                description=(
                    GENERAL_WASTE_COLLECTION_TOMORROW_DESCRIPTION
                ),
            ),
        ]
    )


class TorshavnWasteBinarySensorEntity(
    CoordinatorEntity[TorshavnWasteCoordinator],
    BinarySensorEntity,
):
    """Base class for Tórshavn Waste binary sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TorshavnWasteCoordinator,
        entry: TorshavnWasteConfigEntry,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize a Tórshavn Waste binary sensor."""

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
            model="Ruskinnsavning",
            configuration_url="https://www.kob.fo/",
        )


class TorshavnWasteGreenCollectionTomorrowBinarySensor(
    TorshavnWasteBinarySensorEntity
):
    """Whether green-bin collection is tomorrow."""

    @property
    def is_on(self) -> bool:
        """Return True when green-bin collection is tomorrow."""

        next_collection = (
            self.coordinator.data.next_green_collection
        )

        return (
            next_collection is not None
            and next_collection.days_until == 1
        )


class TorshavnWasteGeneralWasteTomorrowBinarySensor(
    TorshavnWasteBinarySensorEntity
):
    """Whether general-waste collection is tomorrow."""

    @property
    def available(self) -> bool:
        """Return whether general-waste data is available."""

        return (
            super().available
            and self.coordinator.data
            .next_general_waste_collection
            is not None
        )

    @property
    def is_on(self) -> bool | None:
        """Return True when general-waste collection is tomorrow."""

        next_collection = (
            self.coordinator.data
            .next_general_waste_collection
        )

        if next_collection is None:
            return None

        return next_collection.days_until == 1