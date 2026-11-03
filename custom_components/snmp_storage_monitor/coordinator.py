"""SNMP data coordinator."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DEFAULT_SCAN_INTERVAL, HR_STORAGE_FIXED_DISK, HR_STORAGE_RAM
from .snmp import SnmpClient, StorageEntry

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MemoryData:
    size_gb: float
    used_gb: float
    percentage: float


@dataclass(frozen=True, slots=True)
class MonitorData:
    memory: MemoryData | None
    disks: dict[str, StorageEntry]


class SnmpStorageCoordinator(DataUpdateCoordinator[MonitorData]):
    """Fetch all table columns once per polling cycle."""

    def __init__(self, hass: HomeAssistant, client: SnmpClient,
                 scan_interval: int = DEFAULT_SCAN_INTERVAL) -> None:
        self.client = client
        super().__init__(
            hass, _LOGGER, name="SNMP Storage Monitor",
            update_interval=timedelta(seconds=scan_interval)
        )

    async def _async_update_data(self) -> MonitorData:
        try:
            rows = await self.client.async_get_storage_table()
            ram_rows = [r for r in rows if r.storage_type == HR_STORAGE_RAM]
            ram = max(ram_rows, key=lambda r: r.size_bytes) if ram_rows else None
            memory = None
            if ram and ram.size > 0:
                memory = MemoryData(
                    ram.size_bytes / 1024**3,
                    ram.used_bytes / 1024**3,
                    ram.used / ram.size * 100,
                )
            disks = {
                r.key: r for r in rows
                if r.storage_type == HR_STORAGE_FIXED_DISK
            }
            return MonitorData(memory, disks)
        except Exception as err:
            raise UpdateFailed(f"SNMP update failed: {err}") from err
