"""Config flow for the Tórshavn Waste integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
)

from .api import (
    GreenCalendar,
    GreenCalendarDataError,
    SettlementMatch,
    StreetMatch,
    normalize_settlement_name,
    normalize_street_name,
)
from .const import (
    CONF_AREA,
    CONF_SETTLEMENT,
    CONF_STREET,
    DOMAIN,
)


class TorshavnWasteConfigFlow(
    ConfigFlow,
    domain=DOMAIN,
):
    """Handle a config flow for Tórshavn Waste."""

    VERSION = 1
    MINOR_VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""

        self._calendar: GreenCalendar | None = None

        self._street_input: str | None = None
        self._street_match: StreetMatch | None = None
        self._street_options: dict[str, StreetMatch] = {}

    async def _async_get_calendar(
        self,
    ) -> GreenCalendar:
        """Load the green calendar without blocking Home Assistant."""

        if self._calendar is None:
            self._calendar = (
                await self.hass.async_add_executor_job(
                    GreenCalendar
                )
            )

        return self._calendar

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the first configuration step."""

        errors: dict[str, str] = {}

        if user_input is not None:
            street_input = str(
                user_input[CONF_STREET]
            ).strip()

            if not street_input:
                errors[CONF_STREET] = "street_not_found"
            else:
                self._street_input = street_input

                try:
                    calendar = (
                        await self._async_get_calendar()
                    )
                except GreenCalendarDataError:
                    return self.async_abort(
                        reason="calendar_data_error"
                    )

                exact_match = calendar.find_street(
                    street_input
                )

                if exact_match is not None:
                    return await self._async_handle_street_match(
                        exact_match
                    )

                suggestions = calendar.search_streets(
                    street_input,
                    limit=20,
                )

                if suggestions:
                    self._street_options = {
                        match.street: match
                        for match in suggestions
                    }

                    return await self.async_step_select_street()

                return await self.async_step_settlement()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_STREET
                    ): TextSelector(
                        TextSelectorConfig()
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_select_street(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Let the user confirm a suggested street."""

        errors: dict[str, str] = {}

        if not self._street_options:
            return self.async_abort(
                reason="no_street_suggestions"
            )

        if user_input is not None:
            selected_street = str(
                user_input[CONF_STREET]
            )

            street_match = self._street_options.get(
                selected_street
            )

            if street_match is None:
                errors["base"] = (
                    "invalid_street_selection"
                )
            else:
                return await self._async_handle_street_match(
                    street_match
                )

        options = [
            SelectOptionDict(
                value=street,
                label=self._street_option_label(match),
            )
            for street, match
            in self._street_options.items()
        ]

        return self.async_show_form(
            step_id="select_street",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_STREET
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_settlement(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """
        Ask for a settlement when the street was not listed.

        Some areas in the source calendar cover every address
        in a settlement, regardless of whether the individual
        street is printed in the street list.
        """

        if self._street_input is None:
            return self.async_abort(
                reason="missing_street"
            )

        errors: dict[str, str] = {}

        if user_input is not None:
            settlement_input = str(
                user_input[CONF_SETTLEMENT]
            ).strip()

            try:
                calendar = await self._async_get_calendar()
            except GreenCalendarDataError:
                return self.async_abort(
                    reason="calendar_data_error"
                )

            settlement_match = calendar.find_settlement(
                settlement_input
            )

            if settlement_match is None:
                errors["base"] = "settlement_not_found"
            else:
                return await self._async_create_settlement_entry(
                    settlement_match
                )

        return self.async_show_form(
            step_id="settlement",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SETTLEMENT
                    ): TextSelector(
                        TextSelectorConfig()
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "street": self._street_input,
            },
        )

    async def async_step_area(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Let the user choose an area for an ambiguous street."""

        if self._street_match is None:
            return self.async_abort(
                reason="missing_street"
            )

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                selected_area = int(
                    user_input[CONF_AREA]
                )
            except (TypeError, ValueError):
                errors["base"] = "invalid_area"
            else:
                if (
                    selected_area
                    not in self._street_match.areas
                ):
                    errors["base"] = "invalid_area"
                else:
                    return await self._async_create_street_entry(
                        street_match=self._street_match,
                        area=selected_area,
                    )

        area_options = [
            SelectOptionDict(
                value=str(area),
                label=f"Øki {area}",
            )
            for area in self._street_match.areas
        ]

        return self.async_show_form(
            step_id="area",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_AREA
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=area_options,
                        )
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "street": self._street_match.street,
            },
        )

    async def _async_handle_street_match(
        self,
        street_match: StreetMatch,
    ) -> ConfigFlowResult:
        """Continue with a matched street."""

        self._street_match = street_match

        if street_match.is_ambiguous:
            return await self.async_step_area()

        return await self._async_create_street_entry(
            street_match=street_match,
            area=street_match.areas[0],
        )

    async def _async_create_street_entry(
        self,
        street_match: StreetMatch,
        area: int,
    ) -> ConfigFlowResult:
        """Create an entry based on a listed street."""

        unique_id = (
            f"street-"
            f"{normalize_street_name(street_match.street)}"
            f"-area-{area}"
        )

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=street_match.street,
            data={
                CONF_STREET: street_match.street,
                CONF_AREA: area,
            },
        )

    async def _async_create_settlement_entry(
        self,
        settlement_match: SettlementMatch,
    ) -> ConfigFlowResult:
        """Create an entry based on a settlement-wide area."""

        if self._street_input is None:
            return self.async_abort(
                reason="missing_street"
            )

        street = self._street_input
        settlement = settlement_match.settlement
        area = settlement_match.area

        unique_id = (
            f"address-"
            f"{normalize_street_name(street)}"
            f"-"
            f"{normalize_settlement_name(settlement)}"
            f"-area-{area}"
        )

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"{street}, {settlement}",
            data={
                CONF_STREET: street,
                CONF_SETTLEMENT: settlement,
                CONF_AREA: area,
            },
        )

    @staticmethod
    def _street_option_label(
        street_match: StreetMatch,
    ) -> str:
        """Return a readable label for a street suggestion."""

        areas = ", ".join(
            str(area)
            for area in street_match.areas
        )

        if street_match.is_ambiguous:
            return (
                f"{street_match.street} "
                f"(øki {areas})"
            )

        return (
            f"{street_match.street} "
            f"(øki {street_match.areas[0]})"
        )