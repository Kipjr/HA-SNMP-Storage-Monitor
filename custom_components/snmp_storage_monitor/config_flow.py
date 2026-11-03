"""Config and options flows."""
from __future__ import annotations
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import (
    CONF_COMMUNITY, CONF_ENABLED_SENSORS, CONF_HOST, CONF_PORT,
    CONF_SCAN_INTERVAL, DEFAULT_COMMUNITY, DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL, DISK_PREFIX, DOMAIN, HR_STORAGE_FIXED_DISK,
    HR_STORAGE_RAM, MEMORY_KEY, MAX_SCAN_INTERVAL, MIN_SCAN_INTERVAL,
)
from .exceptions import SnmpConnectionError, SnmpMonitorError, SnmpResponseError
from .snmp import SnmpClient


def _schema(disks: list[str], memory: bool, enabled: set[str],
            interval: int | None = None) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if memory:
        fields[vol.Optional(MEMORY_KEY, default=MEMORY_KEY in enabled)] = selector.BooleanSelector()
    for key in disks:
        item = DISK_PREFIX + key
        fields[vol.Optional(item, default=item in enabled)] = selector.BooleanSelector()
    if interval is not None:
        fields[vol.Required(CONF_SCAN_INTERVAL, default=interval)] = vol.All(
            vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
        )
    return vol.Schema(fields)


def _selected(disks: list[str], memory: bool,
              data: dict[str, Any]) -> list[str]:
    selected = [MEMORY_KEY] if memory and data.get(MEMORY_KEY, False) else []
    selected.extend(
        DISK_PREFIX + key for key in disks
        if data.get(DISK_PREFIX + key, False)
    )
    return selected


class SnmpStorageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            client = SnmpClient(
                user_input[CONF_HOST], user_input[CONF_PORT],
                user_input[CONF_COMMUNITY]
            )
            try:
                await client.async_test_connection()
                rows = await client.async_get_storage_table()
                self._disks = [
                    r.key for r in rows if r.storage_type == HR_STORAGE_FIXED_DISK
                ]
                self._memory = any(r.storage_type == HR_STORAGE_RAM for r in rows)
                self._data = {
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input[CONF_PORT],
                    CONF_COMMUNITY: user_input[CONF_COMMUNITY],
                }
                self._interval = user_input[CONF_SCAN_INTERVAL]
                return await self.async_step_select()
            except SnmpConnectionError:
                errors["base"] = "cannot_connect"
            except SnmpResponseError:
                errors["base"] = "invalid_response"
            except SnmpMonitorError:
                errors["base"] = "invalid_response"
            except Exception:
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT):
                    vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                vol.Required(CONF_COMMUNITY, default=DEFAULT_COMMUNITY): str,
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL):
                    vol.All(vol.Coerce(int), vol.Range(
                        min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL
                    )),
            }),
            errors=errors,
        )

    async def async_step_select(self, user_input=None):
        if user_input is not None:
            selected = _selected(self._disks, self._memory, user_input)
            if not selected:
                return self.async_show_form(
                    step_id="select",
                    data_schema=_schema(self._disks, self._memory, set()),
                    errors={"base": "no_sensors"},
                )
            await self.async_set_unique_id(
                f"{self._data[CONF_HOST]}:{self._data[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._data[CONF_HOST],
                data=self._data,
                options={
                    CONF_ENABLED_SENSORS: selected,
                    CONF_SCAN_INTERVAL: self._interval,
                },
            )
        return self.async_show_form(
            step_id="select",
            data_schema=_schema(self._disks, self._memory, set()),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return SnmpStorageOptionsFlow(config_entry)


class SnmpStorageOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.entry = config_entry

    async def async_step_init(self, user_input=None):
        client = SnmpClient(
            self.entry.data[CONF_HOST], self.entry.data[CONF_PORT],
            self.entry.data[CONF_COMMUNITY]
        )
        try:
            await client.async_test_connection()
            rows = await client.async_get_storage_table()
        except SnmpMonitorError:
            return self.async_abort(reason="cannot_connect")
        disks = [r.key for r in rows if r.storage_type == HR_STORAGE_FIXED_DISK]
        memory = any(r.storage_type == HR_STORAGE_RAM for r in rows)
        current = set(self.entry.options.get(CONF_ENABLED_SENSORS, []))
        interval = self.entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        if user_input is not None:
            selected = _selected(disks, memory, user_input)
            if not selected:
                return self.async_show_form(
                    step_id="init",
                    data_schema=_schema(disks, memory, current, interval),
                    errors={"base": "no_sensors"},
                )
            return self.async_create_entry(title="", data={
                CONF_ENABLED_SENSORS: selected,
                CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
            })
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(disks, memory, current, interval),
        )
