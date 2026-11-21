"""Config and options flows."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    AUTH_PROTOCOLS,
    CONF_AUTH_KEY,
    CONF_AUTH_PROTOCOL,
    CONF_COMMUNITY,
    CONF_ENABLED_SENSORS,
    CONF_DISKS_SEPARATE_DEVICE,
    CONF_HOST,
    CONF_PORT,
    CONF_PRIV_KEY,
    CONF_PRIV_PROTOCOL,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VERSION,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DISK_PREFIX,
    DOMAIN,
    HR_STORAGE_FIXED_DISK,
    HR_STORAGE_RAM,
    MAX_SCAN_INTERVAL,
    MEMORY_KEY,
    MIN_SCAN_INTERVAL,
    PRIV_PROTOCOLS,
    SNMP_VERSIONS,
)
from .exceptions import SnmpMonitorError
from .snmp import SnmpClient, StorageEntry

_LOGGER = logging.getLogger(__name__)


def _version_schema() -> vol.Schema:
    """Build the initial host and SNMP version schema."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=65535)
            ),
            vol.Required(CONF_VERSION, default="3"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(SNMP_VERSIONS),
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


def _credential_schema(version: str) -> vol.Schema:
    """Build the credential schema for the selected SNMP version."""
    fields: dict[Any, Any] = {}
    if version in ("1", "2c"):
        fields[vol.Required(CONF_COMMUNITY, default="public")] = str
    else:
        fields.update(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(
                    CONF_AUTH_PROTOCOL, default="none"
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(AUTH_PROTOCOLS),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_AUTH_KEY, default=""): str,
                vol.Required(
                    CONF_PRIV_PROTOCOL, default="none"
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(PRIV_PROTOCOLS),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_PRIV_KEY, default=""): str,
            }
        )
    fields[vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL)] = (
        vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
        )
    )
    return vol.Schema(fields)


def _selection_schema(rows: list[StorageEntry], selected: set[str]) -> vol.Schema:
    """Build the sensor selection schema from discovered storage rows."""
    fields: dict[Any, Any] = {}
    if any(row.storage_type == HR_STORAGE_RAM for row in rows):
        fields[
            vol.Optional(MEMORY_KEY, default=MEMORY_KEY in selected)
        ] = selector.BooleanSelector()

    for row in rows:
        if row.storage_type == HR_STORAGE_FIXED_DISK:
            legacy_key = DISK_PREFIX + row.identity
            for metric in ("free_percent", "free_mb"):
                key = f"{DISK_PREFIX}{row.identity}:{metric}"
                default = key in selected or (
                    legacy_key in selected and metric == "free_percent"
                )
                fields[vol.Optional(key, default=default)] = selector.BooleanSelector()
    return vol.Schema(fields)


def _selected(rows: list[StorageEntry], data: dict[str, Any]) -> list[str]:
    """Return enabled sensor keys from the selection form data."""
    selected = [MEMORY_KEY] if data.get(MEMORY_KEY) else []
    selected.extend(
        f"{DISK_PREFIX}{row.identity}:{metric}"
        for row in rows
        if row.storage_type == HR_STORAGE_FIXED_DISK
        for metric in ("free_percent", "free_mb")
        if data.get(f"{DISK_PREFIX}{row.identity}:{metric}")
    )
    return selected


class SnmpStorageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure an SNMP storage monitor."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialise temporary configuration flow data."""
        super().__init__()
        self._connection: dict[str, Any] = {}
        self._rows: list[StorageEntry] = []
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input=None):
        """Collect the target host and SNMP version."""
        if user_input is not None:
            self._connection = dict(user_input)
            _LOGGER.debug(
                "Setup started: host=%s port=%s version=%s",
                self._connection[CONF_HOST],
                self._connection[CONF_PORT],
                self._connection[CONF_VERSION],
            )
            return await self.async_step_credentials()
        return self.async_show_form(step_id="user", data_schema=_version_schema())

    async def async_step_credentials(self, user_input=None):
        """Collect credentials and discover storage rows."""
        errors = {}
        if user_input is not None:
            data = {**self._connection, **user_input}
            try:
                _LOGGER.debug(
                    "Checking SNMP access: host=%s port=%s version=%s",
                    data[CONF_HOST],
                    data[CONF_PORT],
                    data[CONF_VERSION],
                )
                client = SnmpClient(self.hass, data)
                sysname_ok, storage_ok = await client.async_test_permissions()
                _LOGGER.debug(
                    "SNMP permission probes complete: host=%s "
                    "sysName=%s hrStorageDescr=%s",
                    data[CONF_HOST],
                    sysname_ok,
                    storage_ok,
                )
                if sysname_ok and not storage_ok:
                    errors["base"] = "storage_permission"
                    _LOGGER.error(
                        "SNMP permission check failed for %s: sysName is "
                        "readable, but hrStorageDescr is not readable",
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

                _LOGGER.debug("Discovering storage table: host=%s", data[CONF_HOST])
                self._rows = await client.async_get_storage_table()
                _LOGGER.debug(
                    "Storage discovery complete: host=%s rows=%d",
                    data[CONF_HOST],
                    len(self._rows),
                )
                self._data = data
                await self.async_set_unique_id(
                    f"Usage {data[CONF_HOST].lower()}:{data[CONF_PORT]}"
                )
                self._abort_if_unique_id_configured()
                return await self.async_step_select()
            except config_entries.AbortFlow:
                raise
            except SnmpMonitorError as err:
                _LOGGER.error(
                    "SNMP setup failed for %s: %s",
                    data.get(CONF_HOST),
                    err,
                )
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-exception-caught
                _LOGGER.exception("Unexpected SNMP setup failure")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="credentials",
            data_schema=_credential_schema(self._connection[CONF_VERSION]),
            errors=errors,
        )

    async def async_step_select(self, user_input=None):
        """Let the user select memory and disk sensors."""
        if user_input is not None:
            selected = _selected(self._rows, user_input)
            _LOGGER.debug(
                "Sensor selection submitted: host=%s selected_count=%d",
                self._data[CONF_HOST],
                len(selected),
            )
            if not selected:
                return self.async_show_form(
                    step_id="select",
                    data_schema=_selection_schema(self._rows, set()),
                    errors={"base": "no_sensors"},
                )
            _LOGGER.info(
                "Setup completed: host=%s selected_sensors=%d",
                self._data[CONF_HOST],
                len(selected),
            )
            return self.async_create_entry(
                title=self._data[CONF_HOST],
                data=self._data,
                options={
                    CONF_ENABLED_SENSORS: selected,
                    CONF_SCAN_INTERVAL: self._data[CONF_SCAN_INTERVAL],
                    CONF_DISKS_SEPARATE_DEVICE: user_input.get(
                        CONF_DISKS_SEPARATE_DEVICE, False
                    ),
                },
            )
        return self.async_show_form(
            step_id="select",
            data_schema=_selection_schema(self._rows, set()),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return SnmpStorageOptionsFlow(config_entry)


class SnmpStorageOptionsFlow(config_entries.OptionsFlow):
    """Configure enabled sensors and the polling interval."""

    # This flow delegates its work to Home Assistant's config flow framework.
    # pylint: disable=too-few-public-methods

    def __init__(self, config_entry) -> None:
        """Store the configuration entry being edited."""
        self.entry = config_entry

    async def async_step_init(self, user_input=None):
        """Discover available sensors and update their options."""
        try:
            client = SnmpClient(self.hass, self.entry.data)
            await client.async_test_connection()
            rows = await client.async_get_storage_table()
        except SnmpMonitorError as err:
            _LOGGER.error(
                "SNMP options discovery failed for %s: %s",
                self.entry.data[CONF_HOST],
                err,
            )
            return self.async_abort(reason="cannot_connect")

        selected_now = set(self.entry.options.get(CONF_ENABLED_SENSORS, []))
        interval = self.entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        schema = _selection_schema(rows, selected_now)
        schema = schema.extend(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=interval): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                )
            }
        )

        if user_input is not None:
            selected = _selected(rows, user_input)
            if not selected:
                return self.async_show_form(
                    step_id="init",
                    data_schema=schema,
                    errors={"base": "no_sensors"},
                )
            return self.async_create_entry(
                title="",
                data={
                    CONF_ENABLED_SENSORS: selected,
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    CONF_DISKS_SEPARATE_DEVICE: user_input.get(CONF_DISKS_SEPARATE_DEVICE, False),
                },
            )
        return self.async_show_form(step_id="init", data_schema=schema)
