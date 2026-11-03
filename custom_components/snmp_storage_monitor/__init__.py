"""SNMP Storage Monitor integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_COMMUNITY,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import SnmpStorageCoordinator
from .snmp import SnmpClient


PLATFORMS = ["sensor"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up SNMP Storage Monitor from a config entry."""

    client = SnmpClient(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        community=entry.data[CONF_COMMUNITY],
    )

    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        DEFAULT_SCAN_INTERVAL,
    )

    coordinator = SnmpStorageCoordinator(
        hass,
        client,
        scan_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    entry.async_on_unload(
        entry.add_update_listener(async_reload_entry)
    )

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload an integration config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload integration after options change."""

    await hass.config_entries.async_reload(entry.entry_id)
