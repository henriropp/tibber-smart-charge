"""Adds config flow for Tibber integration."""
from copy import deepcopy
import logging
from typing import Any

import aiohttp
import tibber
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_COUNT,
    CONF_NAME,
    CONF_SENSORS,
    UnitOfTime,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get as async_get_entity_reg,
)

from .const import DOMAIN

TIME_HOURS = UnitOfTime.HOURS

DATA_SCHEMA = vol.Schema({vol.Required(CONF_ACCESS_TOKEN): str})

_LOGGER = logging.getLogger(__name__)


class TibberSmartChargeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tibber integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        self._async_abort_entries_match()

        if user_input is not None:
            access_token = user_input[CONF_ACCESS_TOKEN].replace(" ", "")

            tibber_connection = tibber.Tibber(
                access_token=access_token,
                websession=async_get_clientsession(self.hass),
            )

            errors = {}

            try:
                await tibber_connection.update_info()
            except TimeoutError:
                errors[CONF_ACCESS_TOKEN] = "timeout"
            except aiohttp.ClientError:
                errors[CONF_ACCESS_TOKEN] = "cannot_connect"
            except tibber.InvalidLogin:
                errors[CONF_ACCESS_TOKEN] = "invalid_access_token"

            if errors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=DATA_SCHEMA,
                    errors=errors,
                )

            unique_id = tibber_connection.user_id
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            user_input[CONF_SENSORS] = []
            return self.async_create_entry(
                title=tibber_connection.name,
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors={},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        entity_registry = async_get_entity_reg(self.hass)
        entries = async_entries_for_config_entry(
            entity_registry, self.config_entry.entry_id
        )
        all_sensors = {e.entity_id: e.original_name for e in entries}
        sensors_map = {e.entity_id: e for e in entries}

        if user_input is not None:
            updated_sensors = (
                deepcopy(self.config_entry.options[CONF_SENSORS])
                if CONF_SENSORS in self.config_entry.options
                else []
            )

            removed_sensors = [
                entity_id
                for entity_id in sensors_map.keys()
                if entity_id not in user_input[CONF_SENSORS]
            ]
            for entity_id in removed_sensors:
                # Unregister from HA
                entity_registry.async_remove(entity_id)
                # Remove from our configured repos.
                entry = sensors_map[entity_id]
                entry_name = entry.unique_id
                updated_sensors = [
                    e for e in updated_sensors if e[CONF_NAME] != entry_name
                ]

            if CONF_NAME in user_input:
                updated_sensors.append(
                    {
                        "name": user_input[CONF_NAME],
                        "count": user_input.get(CONF_COUNT, user_input[CONF_NAME]),
                        "h": user_input.get(TIME_HOURS, user_input[CONF_NAME]),
                    }
                )

            if not errors:
                return self.async_create_entry(
                    title="", data={CONF_SENSORS: updated_sensors}
                )

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SENSORS, default=list(all_sensors.keys())
                ): cv.multi_select(all_sensors),
                vol.Optional(CONF_NAME): str,
                vol.Optional(CONF_COUNT): int,
                vol.Optional(TIME_HOURS): int,
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )
