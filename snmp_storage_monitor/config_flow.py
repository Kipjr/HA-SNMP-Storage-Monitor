"""Config flow for SNMP Storage Monitor."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PORT
from homeassistant.helpers import selector

from .const import (
    CONF_COMMUNITY, CONF_ENABLED_SENSORS, CONF_HOST, CONF_SCAN_INTERVAL,
    DEFAULT_COMMUNITY, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DISK_PREFIX,
    DOMAIN, MEMORY_KEY, MAX_SCAN_INTERVAL, MIN_SCAN_INTERVAL,
)
from .exceptions import SnmpConnectionError, SnmpMonitorError, SnmpResponseError
from .snmp import SnmpClient


def _selection_schema(discovered: list[str], enabled: set[str]) -> vol.Schema:
    fields: dict[Any, Any] = {
        vol.Optional(MEMORY_KEY, default=MEMORY_KEY in enabled):
            selector.BooleanSelector(),
    }
    for name in discovered:
        key = f"{DISK_PREFIX}{name}"
        fields[vol.Optional(key, default=key in enabled)] = selector.BooleanSelector()
    return vol.Schema(fields)


def _selected(discovered: list[str], user_input: dict[str, Any]) -> list[str]:
    selected = [MEMORY_KEY] if user_input.get(MEMORY_KEY, False) else []
    selected.extend(
        f"{DISK_PREFIX}{name}"
        for name in discovered
        if user_input.get(f"{DISK_PREFIX}{name}", False)
    )
    return selected


class SnmpStorageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle setup."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: list[str] = []
        self._data: dict[str, Any] = {}
        self._scan_interval = DEFAULT_SCAN_INTERVAL

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Collect SNMP endpoint settings and discover storage."""
        errors: dict[str, str] = {}
        if user_input is not None:
            client = SnmpClient(
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input[CONF_COMMUNITY],
            )
            try:
                await client.async_test_connection()
                self._data = {
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input[CONF_PORT],
                    CONF_COMMUNITY: user_input[CONF_COMMUNITY],
                }
                self._scan_interval = user_input[CONF_SCAN_INTERVAL]
                self._discovered = list(
                    (await client.async_get_storage()).keys()
                )
                return await self.async_step_select()
            except SnmpConnectionError:
                errors["base"] = "cannot_connect"
            except SnmpResponseError:
                errors["base"] = "invalid_response"
            except Exception:
                errors["base"] = "unknown"

        schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=65535)
            ),
            vol.Required(CONF_COMMUNITY, default=DEFAULT_COMMUNITY): str,
            vol.Required(
                CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
            ),
        })
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_select(self, user_input: dict[str, Any] | None = None):
        """Let the user select discovered sensors."""
        if user_input is not None:
            await self.async_set_unique_id(
                f"{self._data[CONF_HOST]}:{self._data[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._data[CONF_HOST],
                data=self._data,
                options={
                    CONF_ENABLED_SENSORS: _selected(
                        self._discovered, user_input
                    ),
                    CONF_SCAN_INTERVAL: self._scan_interval,
                },
            )

        return self.async_show_form(
            step_id="select",
            data_schema=_selection_schema(self._discovered, set()),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return SnmpStorageOptionsFlow(config_entry)


class SnmpStorageOptionsFlow(config_entries.OptionsFlow):
    """Handle sensor selection and polling changes."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry
        self._discovered: list[str] = []

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Rediscover disks and update selection."""
        client = SnmpClient(
            self._entry.data[CONF_HOST],
            self._entry.data[CONF_PORT],
            self._entry.data[CONF_COMMUNITY],
        )
        try:
            self._discovered = list(
                (await client.async_get_storage()).keys()
            )
        except SnmpMonitorError:
            return self.async_abort(reason="cannot_connect")

        current = set(
            self._entry.options.get(CONF_ENABLED_SENSORS, [])
        )
        current_interval = self._entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_ENABLED_SENSORS: _selected(
                        self._discovered, user_input
                    ),
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                },
            )

        schema = _selection_schema(self._discovered, current)
        schema = schema.extend({
            vol.Required(
                CONF_SCAN_INTERVAL, default=current_interval
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
            )
        })
        return self.async_show_form(
            step_id="init", data_schema=schema
        )
