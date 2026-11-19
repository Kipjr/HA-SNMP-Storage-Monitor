"""Storage sensors."""

import hashlib

from homeassistant.const import PERCENTAGE, UnitOfInformation

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ENABLED_SENSORS, DISK_PREFIX, DOMAIN, MEMORY_KEY


# Home Assistant supplies hass as part of the platform setup signature.
# pylint: disable=unused-argument
async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up the selected storage sensors."""
    coordinator = entry.runtime_data
    enabled = set(entry.options.get(CONF_ENABLED_SENSORS, []))
    entities = []

    if MEMORY_KEY in enabled:
        entities.append(MemorySensor(coordinator, entry))

    for item in enabled:
        if item.startswith(DISK_PREFIX):
            parts = item[len(DISK_PREFIX):].rsplit(":", 1)
            if len(parts) == 2 and parts[1] in DiskSensor.METRICS:
                entities.append(DiskSensor(coordinator, entry, parts[0], parts[1]))

    async_add_entities(entities)


class BaseStorageSensor(CoordinatorEntity, SensorEntity):
    """Common device metadata for storage sensors."""

    # Entity classes expose their state through Home Assistant properties.
    # pylint: disable=too-few-public-methods

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry) -> None:
        """Initialise the shared coordinator entity."""
        super().__init__(coordinator)
        self.entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return the monitored host device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=f"SNMP {self.entry.title}",
            manufacturer="SNMP",
            model="Storage Monitor",
        )


class MemorySensor(BaseStorageSensor):
    """Report memory usage as a percentage."""

    # Entity state is exposed through Home Assistant properties.
    # pylint: disable=too-few-public-methods

    _attr_name = "Memory"
    _attr_icon = "mdi:memory"
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, entry) -> None:
        """Initialise the memory sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_memory"

    @property
    def native_value(self) -> float | None:
        """Return current memory usage percentage."""
        data = self.coordinator.data.memory
        return round(data.percentage, 1) if data else None

    @property
    def extra_state_attributes(self) -> dict[str, float]:
        """Return memory size and used capacity in gigabytes."""
        data = self.coordinator.data.memory
        if not data:
            return {}
        return {
            "size_gb": round(data.size_gb, 2),
            "used_gb": round(data.used_gb, 2),
        }


class DiskSensor(BaseStorageSensor):
    """Report usage for one fixed disk."""

    # Entity state is exposed through Home Assistant properties.
    # pylint: disable=too-few-public-methods

    _attr_icon = "mdi:harddisk"
    METRICS = {"free_percent", "free_bytes", "used_percent"}

    def __init__(self, coordinator, entry, identity: str, metric: str) -> None:
        """Initialise the disk sensor for a storage identity."""
        super().__init__(coordinator, entry)
        self.identity = identity
        self.metric = metric
        identity_token = (\n            "root" if identity == "/"\n            else hashlib.sha256(identity.encode()).hexdigest()\n        )
        self._attr_unique_id = f"{entry.entry_id}_disk_{identity_token}_{metric}"
        self._attr_native_unit_of_measurement = (\n            PERCENTAGE if metric.endswith("percent") else UnitOfInformation.BYTES\n        )

    @property
    def name(self) -> str:
        """Return the current disk name."""
        disk = self.coordinator.data.disks.get(self.identity)
        metric_name = {\n            "free_percent": "Free (%)",\n            "free_bytes": "Free",\n            "used_percent": "Used (%)",\n        }[self.metric]
        return f"{disk.name} {metric_name}" if disk else f"{self.identity} {metric_name}"

    @property
    def native_value(self) -> float | None:
        """Return the selected disk metric."""
        disk = self.coordinator.data.disks.get(self.identity)
        if not disk or not disk.size:
            return None
        if self.metric == "free_percent":
            return (disk.size - disk.used) / disk.size * 100
        if self.metric == "free_bytes":
            return disk.size_bytes - disk.used_bytes
        return disk.used / disk.size * 100

    @property
    def extra_state_attributes(self) -> dict[str, float]:
        """Return disk size and used capacity in gigabytes."""
        disk = self.coordinator.data.disks.get(self.identity)
        if not disk:
            return {}
        return {
            "size_gb": disk.size_bytes / 1024**3,
            "used_gb": disk.used_bytes / 1024**3,
            "free_gb": (disk.size_bytes - disk.used_bytes) / 1024**3,
        }
