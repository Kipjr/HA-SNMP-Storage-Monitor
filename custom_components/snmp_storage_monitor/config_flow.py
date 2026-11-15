"""Config and options flows."""
from __future__ import annotations
import logging
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import *
from .exceptions import SnmpMonitorError
from .snmp import SnmpClient

_LOGGER = logging.getLogger(__name__)

def _version_schema():
    return vol.Schema({
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Required(CONF_VERSION, default="2c"): selector.SelectSelector(
            selector.SelectSelectorConfig(options=list(SNMP_VERSIONS), mode=selector.SelectSelectorMode.DROPDOWN)),
    })

def _credential_schema(version):
    fields: dict[Any, Any] = {}
    if version in ("1", "2c"):
        fields[vol.Required(CONF_COMMUNITY, default="public")] = str
    else:
        fields.update({
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_AUTH_PROTOCOL, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=list(AUTH_PROTOCOLS), mode=selector.SelectSelectorMode.DROPDOWN)),
            vol.Optional(CONF_AUTH_KEY, default=""): str,
            vol.Required(CONF_PRIV_PROTOCOL, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=list(PRIV_PROTOCOLS), mode=selector.SelectSelectorMode.DROPDOWN)),
            vol.Optional(CONF_PRIV_KEY, default=""): str,
        })
    fields[vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL)] = vol.All(
        vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL))
    return vol.Schema(fields)

def _selection_schema(rows, selected):
    fields: dict[Any, Any] = {}
    if any(r.storage_type == HR_STORAGE_RAM for r in rows):
        fields[vol.Optional(MEMORY_KEY, default=MEMORY_KEY in selected)] = selector.BooleanSelector()
    for row in rows:
        if row.storage_type == HR_STORAGE_FIXED_DISK:
            key = DISK_PREFIX + row.identity
            fields[vol.Optional(key, default=key in selected)] = selector.BooleanSelector()
    return vol.Schema(fields)

def _selected(rows, data):
    selected = [MEMORY_KEY] if data.get(MEMORY_KEY) else []
    selected.extend(DISK_PREFIX + r.identity for r in rows
        if r.storage_type == HR_STORAGE_FIXED_DISK and data.get(DISK_PREFIX + r.identity))
    return selected

class SnmpStorageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self._connection = dict(user_input)
            return await self.async_step_credentials()
        return self.async_show_form(step_id="user", data_schema=_version_schema())

    async def async_step_credentials(self, user_input=None):
        errors = {}
        if user_input is not None:
            data = {**self._connection, **user_input}
            try:
                client = SnmpClient(self.hass, data)
                sysname_ok, storage_ok = await client.async_test_permissions()
                if sysname_ok and not storage_ok:
                    errors["base"] = "storage_permission"
                    _LOGGER.error(
                        "SNMP permission check failed for %s: sysName is readable, "
                        "but hrStorageDescr is not readable",
                        data.get(CONF_HOST),
                    )
                    return self.async_show_form(
                        step_id="credentials",
                        data_schema=_credential_schema(self._connection[CONF_VERSION]),
                        errors=errors,
                    )
                if not sysname_ok and not storage_ok:
                    errors["base"] = "snmp_probe_failed"
                    _LOGGER.error(
                        "SNMP permission/connectivity check failed for %s: "
                        "neither sysName nor hrStorageDescr is readable",
                        data.get(CONF_HOST),
                    )
                    return self.async_show_form(
                        step_id="credentials",
                        data_schema=_credential_schema(self._connection[CONF_VERSION]),
                        errors=errors,
                    )
                self._rows = await client.async_get_storage_table()
                self._data = data
                await self.async_set_unique_id(f"{data[CONF_HOST].lower()}:{data[CONF_PORT]}")
                self._abort_if_unique_id_configured()
                return await self.async_step_select()
            except SnmpMonitorError as err:
                _LOGGER.error("SNMP setup failed for %s: %s", data.get(CONF_HOST), err)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected SNMP setup failure")
                errors["base"] = "unknown"
        return self.async_show_form(step_id="credentials",
            data_schema=_credential_schema(self._connection[CONF_VERSION]), errors=errors)

    async def async_step_select(self, user_input=None):
        if user_input is not None:
            selected = _selected(self._rows, user_input)
            if not selected:
                return self.async_show_form(step_id="select",
                    data_schema=_selection_schema(self._rows, set()), errors={"base": "no_sensors"})
            return self.async_create_entry(title=self._data[CONF_HOST], data=self._data,
                options={CONF_ENABLED_SENSORS: selected, CONF_SCAN_INTERVAL: self._data[CONF_SCAN_INTERVAL]})
        return self.async_show_form(step_id="select", data_schema=_selection_schema(self._rows, set()))

    @staticmethod
    def async_get_options_flow(config_entry):
        return SnmpStorageOptionsFlow(config_entry)

class SnmpStorageOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.entry = config_entry
    async def async_step_init(self, user_input=None):
        try:
            client = SnmpClient(self.hass, self.entry.data)
            await client.async_test_connection()
            rows = await client.async_get_storage_table()
        except SnmpMonitorError as err:
            _LOGGER.error("SNMP options discovery failed for %s: %s", self.entry.data[CONF_HOST], err)
            return self.async_abort(reason="cannot_connect")
        selected_now = set(self.entry.options.get(CONF_ENABLED_SENSORS, []))
        interval = self.entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        schema = _selection_schema(rows, selected_now)
        schema = schema.extend({vol.Required(CONF_SCAN_INTERVAL, default=interval):
            vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL))})
        if user_input is not None:
            selected = _selected(rows, user_input)
            if not selected:
                return self.async_show_form(step_id="init", data_schema=schema, errors={"base": "no_sensors"})
            return self.async_create_entry(title="", data={CONF_ENABLED_SENSORS: selected,
                CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]})
        return self.async_show_form(step_id="init", data_schema=schema)
