"""SNMP coordinator."""

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DEFAULT_SCAN_INTERVAL, HR_STORAGE_FIXED_DISK, HR_STORAGE_RAM
from .snmp import SnmpClient, StorageEntry

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MemoryData:
    """Memory usage values in gigabytes and percent."""

    size_gb: float
    used_gb: float
    percentage: float


@dataclass(frozen=True, slots=True)
class MonitorData:
    """Current memory and disk data from the monitored host."""

    memory: MemoryData | None
    disks: dict[str, StorageEntry]


class SnmpStorageCoordinator(DataUpdateCoordinator[MonitorData]):
    """Fetch and organise storage data from an SNMP host."""

    # The coordinator is a data container and update orchestrator.
    # pylint: disable=too-few-public-methods

    def __init__(
        self,
        hass: HomeAssistant,
        client: SnmpClient,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialise the storage coordinator."""
        self.client = client
        super().__init__(
            hass,
            _LOGGER,
            name="SNMP Storage Monitor",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> MonitorData:
        """Fetch storage rows and split memory from fixed disks."""
        try:
            rows = await self.client.async_get_storage_table()
            ram_rows = [row for row in rows if row.storage_type == HR_STORAGE_RAM]
            ram = max(ram_rows, key=lambda row: row.size_bytes) if ram_rows else None
            memory = (
                MemoryData(
                    ram.size_bytes / 1024**3,
                    ram.used_bytes / 1024**3,
                    ram.used / ram.size * 100,
                )
                if ram and ram.size
                else None
            )
            disks = {
                row.identity: row
                for row in rows
                if row.storage_type == HR_STORAGE_FIXED_DISK
            }
            return MonitorData(memory, disks)
        except Exception as err:
            _LOGGER.exception("SNMP storage polling failed")
            raise UpdateFailed("SNMP storage polling failed") from err
