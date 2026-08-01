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
from .bag_delivery import (
    BagDeliveryResult,
    next_bag_delivery,
)
from .const import DOMAIN
from .coordinator import (
    TorshavnWasteCoordinator,
    TorshavnWasteData,
)
from .formatting import (
    format_date_fo,
    format_month_fo,
    relative_days_fo,
    weekday_name_fo,
)

PARALLEL_UPDATES = 0


NEXT_GREEN_COLLECTION_DESCRIPTION = SensorEntityDescription(
    key="next_green_collection",
    translation_key="next_green_collection",
    device_class=SensorDeviceClass.DATE,
    icon="mdi:recycle",
)

NEXT_GENERAL_WASTE_COLLECTION_DESCRIPTION = (
    SensorEntityDescription(
        key="next_general_waste_collection",
        translation_key="next_general_waste_collection",
        device_class=SensorDeviceClass.DATE,
        icon="mdi:trash-can",
    )
)

NEXT_BAG_DELIVERY_DESCRIPTION = SensorEntityDescription(
    key="next_bag_delivery",
    translation_key="next_bag_delivery",
    icon="mdi:bag-personal",
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
                description=(
                    NEXT_GREEN_COLLECTION_DESCRIPTION
                ),
            ),
            TorshavnWasteNextGeneralWasteCollectionSensor(
                coordinator=coordinator,
                entry=entry,
                description=(
                    NEXT_GENERAL_WASTE_COLLECTION_DESCRIPTION
                ),
            ),
            TorshavnWasteNextBagDeliverySensor(
                coordinator=coordinator,
                entry=entry,
                description=NEXT_BAG_DELIVERY_DESCRIPTION,
            ),
        ]
    )


class TorshavnWasteSensorEntity(
    CoordinatorEntity[TorshavnWasteCoordinator],
    SensorEntity,
):
    """Base class for Tórshavn Waste sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TorshavnWasteCoordinator,
        entry: TorshavnWasteConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize a Tórshavn Waste sensor."""

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


class TorshavnWasteNextGreenCollectionSensor(
    TorshavnWasteSensorEntity
):
    """Sensor showing the next green-bin collection."""

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
        """Return additional green-bin information."""

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

        if next_collection is None:
            attributes.update(
                {
                    "days_until": None,
                    "formatted_date": None,
                    "weekday_name_fo": None,
                    "relative_text": None,
                }
            )

            return attributes

        attributes.update(
            {
                "days_until": next_collection.days_until,
                "formatted_date": format_date_fo(
                    next_collection.collection_date
                ),
                "weekday_name_fo": weekday_name_fo(
                    next_collection.collection_date
                ),
                "relative_text": relative_days_fo(
                    next_collection.days_until
                ),
            }
        )

        return attributes


class TorshavnWasteNextGeneralWasteCollectionSensor(
    TorshavnWasteSensorEntity
):
    """Sensor showing the next general-waste collection."""

    @property
    def available(self) -> bool:
        """Return whether general-waste data is available."""

        data = self.coordinator.data

        return (
            super().available
            and data.general_waste_area is not None
            and data.next_general_waste_collection is not None
        )

    @property
    def native_value(self) -> date | None:
        """Return the next general-waste collection date."""

        next_collection = (
            self.coordinator.data
            .next_general_waste_collection
        )

        if next_collection is None:
            return None

        return next_collection.collection_date

    @property
    def extra_state_attributes(
        self,
    ) -> dict[str, Any]:
        """Return additional general-waste information."""

        data: TorshavnWasteData = self.coordinator.data
        area = data.general_waste_area
        next_collection = (
            data.next_general_waste_collection
        )

        attributes: dict[str, Any] = {
            "street": data.street,
            "settlement": data.settlement,
            "error": data.general_waste_error,
        }

        if area is None:
            attributes.update(
                {
                    "city": None,
                    "zip_code": None,
                    "route_id": None,
                    "weekday": None,
                    "weekday_name": None,
                    "object_id": None,
                    "global_id": None,
                    "days_until": None,
                    "formatted_date": None,
                    "weekday_name_fo": None,
                    "relative_text": None,
                    "is_holiday": None,
                    "holiday_name": None,
                    "schedule_may_be_changed": None,
                }
            )

            return attributes

        attributes.update(
            {
                "city": area.city,
                "zip_code": area.zip_code,
                "route_id": area.route_id,
                "weekday": area.weekday,
                "weekday_name": area.weekday_name,
                "object_id": area.object_id,
                "global_id": area.global_id,
                "days_until": (
                    next_collection.days_until
                    if next_collection is not None
                    else None
                ),
                "formatted_date": (
                    format_date_fo(
                        next_collection.collection_date
                    )
                    if next_collection is not None
                    else None
                ),
                "weekday_name_fo": (
                    weekday_name_fo(
                        next_collection.collection_date
                    )
                    if next_collection is not None
                    else None
                ),
                "relative_text": (
                    relative_days_fo(
                        next_collection.days_until
                    )
                    if next_collection is not None
                    else None
                ),
                "is_holiday": (
                    next_collection.is_holiday
                    if next_collection is not None
                    else None
                ),
                "holiday_name": (
                    next_collection.holiday_name
                    if next_collection is not None
                    else None
                ),
                "schedule_may_be_changed": (
                    next_collection.schedule_may_be_changed
                    if next_collection is not None
                    else None
                ),
            }
        )

        return attributes


class TorshavnWasteNextBagDeliverySensor(
    TorshavnWasteSensorEntity
):
    """Sensor showing the next bag-delivery month."""

    @property
    def native_value(self) -> str | None:
        """Return the next bag-delivery month as YYYY-MM."""

        result = self._next_delivery()

        if result is None:
            return None

        return (
            f"{result.delivery_year:04d}-"
            f"{result.delivery_month:02d}"
        )

    @property
    def extra_state_attributes(
        self,
    ) -> dict[str, Any]:
        """Return details about the next bag delivery."""

        data: TorshavnWasteData = self.coordinator.data
        result = self._next_delivery()

        attributes: dict[str, Any] = {
            "street": data.street,
            "settlement": data.settlement,
            "calendar_year": data.calendar_year,
            "red_bag_months": list(
                data.red_bag_months
            ),
            "grey_bag_months": list(
                data.grey_bag_months
            ),
        }

        if result is None:
            attributes.update(
                {
                    "delivery_year": None,
                    "delivery_month": None,
                    "months_until": None,
                    "bag_types": [],
                    "formatted_month": None,
                }
            )

            return attributes

        attributes.update(
            {
                "delivery_year": result.delivery_year,
                "delivery_month": result.delivery_month,
                "months_until": result.months_until,
                "bag_types": list(result.bag_types),
                "formatted_month": format_month_fo(
                    result.delivery_year,
                    result.delivery_month,
                ),
            }
        )

        return attributes

    def _next_delivery(
        self,
    ) -> BagDeliveryResult | None:
        """Calculate the next bag-delivery month."""

        data: TorshavnWasteData = self.coordinator.data

        return next_bag_delivery(
            calendar_year=data.calendar_year,
            red_bag_months=data.red_bag_months,
            grey_bag_months=data.grey_bag_months,
            from_date=date.today(),
        )