"""Storage sensors."""

import hashlib

from homeassistant.const import PERCENTAGE, UnitOfInformation

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ENABLED_SENSORS, CONF_DISKS_SEPARATE_DEVICE, DISK_PREFIX, DOMAIN, MEMORY_KEY


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
            identity, metric = item[len(DISK_PREFIX):].rsplit(":", 1)
            entities.append(DiskSensor(coordinator, entry, identity, metric))

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
        return data.percentage if data else None

    @property
    def extra_state_attributes(self) -> dict[str, float]:
        """Return memory size and used capacity in gigabytes."""
        data = self.coordinator.data.memory
        if not data:
            return {}
        return {
            "size_gb": data.size_gb,
            "used_gb": data.used_gb,
        }


class DiskSensor(BaseStorageSensor):
    """Report selected free-capacity metrics for a fixed disk."""

    # pylint: disable=too-few-public-methods

    _attr_icon = "mdi:harddisk"
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator, entry, identity: str, metric: str) -> None:
        """Initialise a disk metric sensor."""
        super().__init__(coordinator, entry)
        self.identity = identity
        self.metric = metric
        self.separate_device = entry.options.get(CONF_DISKS_SEPARATE_DEVICE, False)
        digest = hashlib.sha256(identity.encode()).hexdigest()
        self._attr_unique_id = f"{entry.entry_id}_disk_{digest}_{metric}"
        self._attr_native_unit_of_measurement = PERCENTAGE if metric == "free_percent" else "MB"

    @property
    def device_info(self) -> DeviceInfo:
        """Return disk device metadata, optionally separated from the host."""
        if not self.separate_device:
            return super().device_info
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id, "disks")},
            name=f"SNMP {self.entry.title} Disks",
            manufacturer="SNMP",
            model="Storage Monitor Disks",
        )

    @property
    def name(self) -> str:
        """Return the disk metric name."""
        disk = self.coordinator.data.disks.get(self.identity)
        disk_name = "root" if self.identity == "/" else (disk.name if disk else self.identity)
        metric_name = "Free Space (%)" if self.metric == "free_percent" else "Free MB"
        return f"Disk: {disk_name} - {metric_name}"

    @property
    def native_value(self) -> float | None:
        """Return free capacity as percentage or megabytes."""
        disk = self.coordinator.data.disks.get(self.identity)
        if not disk or not disk.size:
            return None
        if self.metric == "free_percent":
            return (disk.size - disk.used) / disk.size * 100
        return (disk.size_bytes - disk.used_bytes) / 1024**2

    @property
    def extra_state_attributes(self) -> dict[str, float]:
        """Return disk size, used and free capacity in GB."""
        disk = self.coordinator.data.disks.get(self.identity)
        if not disk:
            return {}
        return {
            "size_gb": disk.size_bytes / 1024**3,
            "used_gb": disk.used_bytes / 1024**3,
            "free_gb": (disk.size_bytes - disk.used_bytes) / 1024**3,
        }
