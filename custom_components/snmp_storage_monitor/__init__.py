"""SNMP Storage Monitor integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_COMMUNITY,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import SnmpStorageCoordinator
from .snmp import SnmpClient

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an SNMP Storage Monitor config entry."""
    client = SnmpClient(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_COMMUNITY],
    )
    coordinator = SnmpStorageCoordinator(
        hass,
        client,
        entry.options.get(CONF_SCAN_INTERVAL, 60),
    )
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an SNMP Storage Monitor entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
