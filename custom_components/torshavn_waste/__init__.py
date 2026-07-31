"""The Tórshavn Waste integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError

from .api import (
    GreenCalendar,
    GreenCalendarDataError,
)
from .coordinator import TorshavnWasteCoordinator

PLATFORMS: tuple[Platform, ...] = (
    Platform.SENSOR,
)


type TorshavnWasteConfigEntry = ConfigEntry[
    TorshavnWasteCoordinator
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TorshavnWasteConfigEntry,
) -> bool:
    """Set up Tórshavn Waste from a config entry."""

    try:
        calendar = await hass.async_add_executor_job(
            GreenCalendar
        )
    except GreenCalendarDataError as error:
        raise ConfigEntryError(
            f"Could not load green calendar data: {error}"
        ) from error

    coordinator = TorshavnWasteCoordinator(
        hass=hass,
        entry=entry,
        calendar=calendar,
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: TorshavnWasteConfigEntry,
) -> bool:
    """Unload a Tórshavn Waste config entry."""

    return await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )