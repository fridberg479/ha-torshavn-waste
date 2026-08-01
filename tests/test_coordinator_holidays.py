"""Tests for holiday warnings in general-waste scheduling."""

from __future__ import annotations

from datetime import date
import importlib.util
from pathlib import Path
import sys
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
COMPONENT_PATH = (
    ROOT
    / "custom_components"
    / "torshavn_waste"
)


def _install_home_assistant_stubs() -> None:
    """Install minimal Home Assistant modules needed for import."""

    homeassistant = ModuleType("homeassistant")
    config_entries = ModuleType(
        "homeassistant.config_entries"
    )
    core = ModuleType("homeassistant.core")
    helpers = ModuleType("homeassistant.helpers")
    update_coordinator = ModuleType(
        "homeassistant.helpers.update_coordinator"
    )

    class ConfigEntry:
        """Minimal ConfigEntry stub."""

    class HomeAssistant:
        """Minimal HomeAssistant stub."""

    class DataUpdateCoordinator:
        """Minimal DataUpdateCoordinator stub."""

        def __class_getitem__(cls, item):
            return cls

        def __init__(self, *args, **kwargs) -> None:
            pass

    class UpdateFailed(Exception):
        """Minimal UpdateFailed stub."""

    config_entries.ConfigEntry = ConfigEntry
    core.HomeAssistant = HomeAssistant
    update_coordinator.DataUpdateCoordinator = (
        DataUpdateCoordinator
    )
    update_coordinator.UpdateFailed = UpdateFailed

    sys.modules["homeassistant"] = homeassistant
    sys.modules[
        "homeassistant.config_entries"
    ] = config_entries
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules[
        "homeassistant.helpers.update_coordinator"
    ] = update_coordinator


def _install_integration_stubs() -> None:
    """Install minimal integration modules needed for import."""

    package = ModuleType(
        "custom_components.torshavn_waste"
    )
    package.__path__ = [str(COMPONENT_PATH)]

    api = ModuleType(
        "custom_components.torshavn_waste.api"
    )
    arcgis = ModuleType(
        "custom_components.torshavn_waste.arcgis"
    )
    const = ModuleType(
        "custom_components.torshavn_waste.const"
    )

    class CollectionResult:
        """Minimal CollectionResult stub."""

    class GreenCalendar:
        """Minimal GreenCalendar stub."""

    class GreenCalendarError(Exception):
        """Minimal GreenCalendarError stub."""

    class ArcGISWasteError(Exception):
        """Minimal ArcGISWasteError stub."""

    class GeneralWasteArea:
        """Minimal GeneralWasteArea stub."""

    def fetch_general_waste_areas(*args, **kwargs):
        return ()

    api.CollectionResult = CollectionResult
    api.GreenCalendar = GreenCalendar
    api.GreenCalendarError = GreenCalendarError

    arcgis.ArcGISWasteError = ArcGISWasteError
    arcgis.GeneralWasteArea = GeneralWasteArea
    arcgis.fetch_general_waste_areas = (
        fetch_general_waste_areas
    )

    const.CONF_AREA = "area"
    const.CONF_SETTLEMENT = "settlement"
    const.CONF_STREET = "street"
    const.DOMAIN = "torshavn_waste"

    sys.modules["custom_components"] = ModuleType(
        "custom_components"
    )
    sys.modules[
        "custom_components.torshavn_waste"
    ] = package
    sys.modules[
        "custom_components.torshavn_waste.api"
    ] = api
    sys.modules[
        "custom_components.torshavn_waste.arcgis"
    ] = arcgis
    sys.modules[
        "custom_components.torshavn_waste.const"
    ] = const


def _load_module(
    module_name: str,
    file_name: str,
):
    """Load a module from the integration directory."""

    module_path = COMPONENT_PATH / file_name

    spec = importlib.util.spec_from_file_location(
        module_name,
        module_path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Could not load module from {module_path}"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return module


_install_home_assistant_stubs()
_install_integration_stubs()

_load_module(
    "custom_components.torshavn_waste.holidays",
    "holidays.py",
)

coordinator_module = _load_module(
    "custom_components.torshavn_waste.coordinator",
    "coordinator.py",
)

TorshavnWasteCoordinator = (
    coordinator_module.TorshavnWasteCoordinator
)


def test_collection_on_holiday_has_warning() -> None:
    """A collection on Christmas Eve has a warning."""

    result = (
        TorshavnWasteCoordinator
        ._next_general_waste_collection(
            weekday=4,
            from_date=date(2026, 12, 24),
        )
    )

    assert result.collection_date == date(
        2026,
        12,
        24,
    )
    assert result.days_until == 0
    assert result.is_holiday is True
    assert result.holiday_name == "Jólaftan"
    assert result.schedule_may_be_changed is True


def test_upcoming_collection_on_holiday_has_warning() -> None:
    """A future collection date is checked for holidays."""

    result = (
        TorshavnWasteCoordinator
        ._next_general_waste_collection(
            weekday=4,
            from_date=date(2026, 12, 21),
        )
    )

    assert result.collection_date == date(
        2026,
        12,
        24,
    )
    assert result.days_until == 3
    assert result.is_holiday is True
    assert result.holiday_name == "Jólaftan"
    assert result.schedule_may_be_changed is True


def test_collection_on_normal_day_has_no_warning() -> None:
    """A regular collection date has no holiday warning."""

    result = (
        TorshavnWasteCoordinator
        ._next_general_waste_collection(
            weekday=4,
            from_date=date(2026, 8, 3),
        )
    )

    assert result.collection_date == date(
        2026,
        8,
        6,
    )
    assert result.days_until == 3
    assert result.is_holiday is False
    assert result.holiday_name is None
    assert result.schedule_may_be_changed is False


def test_collection_date_is_not_moved() -> None:
    """A holiday warning does not move the collection date."""

    result = (
        TorshavnWasteCoordinator
        ._next_general_waste_collection(
            weekday=5,
            from_date=date(2026, 12, 21),
        )
    )

    assert result.collection_date == date(
        2026,
        12,
        25,
    )
    assert result.holiday_name == "1. Jóladagur"
    assert result.schedule_may_be_changed is True