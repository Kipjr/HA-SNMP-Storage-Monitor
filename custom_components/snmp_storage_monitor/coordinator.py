"""Data update coordinator for SNMP Storage Monitor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL
from .snmp import SnmpClient, StorageEntry

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class MemoryData:
    size_gb: float
    used_gb: float
    percentage: float


@dataclass(slots=True, frozen=True)
class MonitorData:
    memory: MemoryData | None
    disks: dict[str, StorageEntry]


class SnmpStorageCoordinator(DataUpdateCoordinator[MonitorData]):
    """Coordinate one SNMP poll for all entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: SnmpClient,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        self.client = client
        super().__init__(
            hass,
            _LOGGER,
            name="SNMP Storage Monitor",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> MonitorData:
        try:
            memory_size, memory_used, memory_pct = await self.client.async_get_memory()
            memory = MemoryData(memory_size, memory_used, memory_pct)
            disks = await self.client.async_get_storage()
            return MonitorData(memory=memory, disks=disks)
        except Exception as err:
            raise UpdateFailed(str(err)) from err
