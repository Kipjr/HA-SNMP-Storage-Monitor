"""SNMP sensors."""
from __future__ import annotations
import hashlib
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import CONF_ENABLED_SENSORS, DISK_PREFIX, DOMAIN, MEMORY_KEY
from .coordinator import SnmpStorageCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities) -> None:
    coordinator: SnmpStorageCoordinator = entry.runtime_data
    enabled = set(entry.options.get(CONF_ENABLED_SENSORS, []))
    entities: list[SensorEntity] = []
    if MEMORY_KEY in enabled:
        entities.append(MemorySensor(coordinator, entry))
    for item in sorted(enabled):
        if item.startswith(DISK_PREFIX):
            entities.append(DiskSensor(
                coordinator, entry, item.removeprefix(DISK_PREFIX)
            ))
    async_add_entities(entities)


class SnmpSensor(CoordinatorEntity[SnmpStorageCoordinator], SensorEntity):
    _attr_has_entity_name = False

    def __init__(self, coordinator: SnmpStorageCoordinator,
                 entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=f"SNMP {self.entry.title}",
            manufacturer="SNMP",
            model="Storage Monitor",
        )


class MemorySensor(SnmpSensor):
    _attr_name = "Memory"
    _attr_icon = "mdi:memory"
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_memory"

    @property
    def native_value(self):
        data = self.coordinator.data.memory
        return round(data.percentage, 1) if data else None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data.memory
        if data is None:
            return {}
        return {"size_gb": round(data.size_gb, 2),
                "used_gb": round(data.used_gb, 2)}


class DiskSensor(SnmpSensor):
    _attr_icon = "mdi:harddisk"
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, entry, key: str) -> None:
        super().__init__(coordinator, entry)
        self.key = key
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]
        self._attr_unique_id = f"{entry.entry_id}_disk_{digest}"

    @property
    def name(self):
        disk = self.coordinator.data.disks.get(self.key)
        return disk.name if disk else self.key

    @property
    def native_value(self):
        disk = self.coordinator.data.disks.get(self.key)
        if disk is None or disk.size <= 0:
            return None
        return round(disk.used / disk.size * 100, 1)

    @property
    def extra_state_attributes(self):
        disk = self.coordinator.data.disks.get(self.key)
        if disk is None:
            return {}
        return {
            "size_gb": round(disk.size_bytes / 1024**3, 2),
            "used_gb": round(disk.used_bytes / 1024**3, 2),
            "snmp_index": disk.index,
        }
