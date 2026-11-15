"""Storage sensors."""
import hashlib
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import CONF_ENABLED_SENSORS, DISK_PREFIX, DOMAIN, MEMORY_KEY

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    enabled = set(entry.options.get(CONF_ENABLED_SENSORS, []))
    entities = []
    if MEMORY_KEY in enabled: entities.append(MemorySensor(coordinator, entry))
    for item in enabled:
        if item.startswith(DISK_PREFIX):
            entities.append(DiskSensor(coordinator, entry, item[len(DISK_PREFIX):]))
    async_add_entities(entities)

class BaseStorageSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
    @property
    def device_info(self):
        return DeviceInfo(identifiers={(DOMAIN, self.entry.entry_id)},
            name=f"SNMP {self.entry.title}", manufacturer="SNMP", model="Storage Monitor")

class MemorySensor(BaseStorageSensor):
    _attr_name = "Memory"
    _attr_icon = "mdi:memory"
    _attr_native_unit_of_measurement = PERCENTAGE
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_memory"
    @property
    def native_value(self):
        data = self.coordinator.data.memory
        return round(data.percentage, 1) if data else None
    @property
    def extra_state_attributes(self):
        data = self.coordinator.data.memory
        return {"size_gb": round(data.size_gb, 2), "used_gb": round(data.used_gb, 2)} if data else {}

class DiskSensor(BaseStorageSensor):
    _attr_icon = "mdi:harddisk"
    _attr_native_unit_of_measurement = PERCENTAGE
    def __init__(self, coordinator, entry, identity):
        super().__init__(coordinator, entry)
        self.identity = identity
        self._attr_unique_id = f"{entry.entry_id}_disk_{hashlib.sha256(identity.encode()).hexdigest()}"
    @property
    def name(self):
        disk = self.coordinator.data.disks.get(self.identity)
        return disk.name if disk else self.identity
    @property
    def native_value(self):
        disk = self.coordinator.data.disks.get(self.identity)
        return round(disk.used / disk.size * 100, 1) if disk and disk.size else None
    @property
    def extra_state_attributes(self):
        disk = self.coordinator.data.disks.get(self.identity)
        return {"size_gb": round(disk.size_bytes / 1024**3, 2),
            "used_gb": round(disk.used_bytes / 1024**3, 2)} if disk else {}
