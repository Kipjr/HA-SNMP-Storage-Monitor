"""Sensors for SNMP Storage Monitor."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ENABLED_SENSORS, DISK_PREFIX, DOMAIN, MEMORY_KEY
from .coordinator import SnmpStorageCoordinator


@dataclass(frozen=True, slots=True)
class _Selection:
    """Selected sensor."""

    key: str
    name: str


def _disk_unique_suffix(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up selected SNMP storage sensors."""
    coordinator: SnmpStorageCoordinator = entry.runtime_data
    enabled = set(entry.options.get(CONF_ENABLED_SENSORS, []))
    entities: list[SensorEntity] = []

    if MEMORY_KEY in enabled:
        entities.append(MemorySensor(coordinator, entry))

    for key in enabled:
        if key.startswith(DISK_PREFIX):
            name = key.removeprefix(DISK_PREFIX)
            entities.append(DiskSensor(coordinator, entry, name))

    async_add_entities(entities)


class SnmpSensorBase(CoordinatorEntity[SnmpStorageCoordinator], SensorEntity):
    """Base SNMP sensor."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: SnmpStorageCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return the single SNMP device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=f"SNMP {self._entry.title}",
            manufacturer="SNMP",
            model="SNMP Storage Monitor",
        )


class MemorySensor(SnmpSensorBase):
    """Memory usage sensor."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:memory"

    def __init__(
        self,
        coordinator: SnmpStorageCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_memory"
        self._attr_name = "Memory"

    @property
    def native_value(self) -> float | None:
        """Return memory percentage used."""
        memory = self.coordinator.data.memory
        return round(memory.percentage, 1) if memory else None

    @property
    def extra_state_attributes(self) -> dict[str, float]:
        """Return memory size information."""
        memory = self.coordinator.data.memory
        if not memory:
            return {}
        return {
            "size_gb": round(memory.size_gb, 2),
            "used_gb": round(memory.used_gb, 2),
        }


class DiskSensor(SnmpSensorBase):
    """Disk usage sensor identified by the stable disk name."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:harddisk"

    def __init__(
        self,
        coordinator: SnmpStorageCoordinator,
        entry: ConfigEntry,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._disk_name = name
        self._attr_unique_id = (
            f"{entry.entry_id}_disk_{_disk_unique_suffix(name)}"
        )
        self._attr_name = name

    @property
    def native_value(self) -> float | None:
        """Return percentage of disk space used."""
        disk = self.coordinator.data.disks.get(self._disk_name)
        if not disk or disk.size <= 0:
            return None
        return round(disk.used / disk.size * 100, 1)

    @property
    def extra_state_attributes(self) -> dict[str, float | int | str]:
        """Return disk size and current SNMP index."""
        disk = self.coordinator.data.disks.get(self._disk_name)
        if not disk:
            return {}
        size_gb = (disk.size * disk.allocation_unit) / (1024**3)
        used_gb = (disk.used * disk.allocation_unit) / (1024**3)
        return {
            "size_gb": round(size_gb, 2),
            "used_gb": round(used_gb, 2),
            "snmp_index": disk.index,
        }
