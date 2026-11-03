"""SNMP Storage Monitor integration."""
from __future__ import annotations
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import (
    CONF_COMMUNITY, CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL
)
from .coordinator import SnmpStorageCoordinator
from .snmp import SnmpClient

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = SnmpClient(
        entry.data[CONF_HOST], entry.data[CONF_PORT],
        entry.data[CONF_COMMUNITY]
    )
    coordinator = SnmpStorageCoordinator(
        hass, client,
        entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
