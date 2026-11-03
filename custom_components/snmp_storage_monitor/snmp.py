"""Asynchronous SNMP v2c client."""
from __future__ import annotations
from dataclasses import dataclass
import asyncio
import logging
from typing import Any

from pysnmp.hlapi.v1arch.asyncio import (
    CommunityData, ContextData, SnmpEngine, UdpTransportTarget, bulk_cmd, get_cmd
)
from pysnmp.proto.rfc1902 import ObjectName
from pysnmp.proto.rfc1905 import Null

from .const import (
    HR_STORAGE_DESCR_OID, HR_STORAGE_FIXED_DISK, HR_STORAGE_RAM,
    HR_STORAGE_SIZE_OID, HR_STORAGE_TYPE_OID, HR_STORAGE_UNIT_OID,
    HR_STORAGE_USED_OID, SYS_DESCR_OID,
)
from .exceptions import SnmpConnectionError, SnmpMonitorError, SnmpResponseError

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StorageEntry:
    """One hrStorageTable row."""
    index: str
    key: str
    name: str
    storage_type: str
    allocation_unit: int
    size: int
    used: int

    @property
    def size_bytes(self) -> int:
        return self.allocation_unit * self.size

    @property
    def used_bytes(self) -> int:
        return self.allocation_unit * self.used


class SnmpClient:
    """SNMP v2c client. Numeric OIDs avoid runtime MIB loading."""

    def __init__(self, host: str, port: int, community: str) -> None:
        self.host = host
        self.port = port
        self.engine = SnmpEngine()
        self.auth = CommunityData(community, mpModel=1)

    async def _target(self) -> UdpTransportTarget:
        try:
            return await UdpTransportTarget.create(
                (self.host, self.port), timeout=5, retries=1
            )
        except Exception as err:
            raise SnmpConnectionError(str(err)) from err

    async def _get(self, oid: str) -> Any:
        try:
            indication, status, index, values = await get_cmd(
                self.engine, self.auth, await self._target(), ContextData(),
                (ObjectName(oid), Null("")), lookupMib=False
            )
        except SnmpMonitorError:
            raise
        except Exception as err:
            raise SnmpConnectionError(f"SNMP GET {oid}: {err}") from err
        if indication:
            raise SnmpConnectionError(str(indication))
        if status:
            raise SnmpResponseError(
                f"{status.prettyPrint()} at varbind index {index}"
            )
        if not values:
            raise SnmpResponseError(f"No value returned for OID {oid}")
        return values[0][1]

    async def _walk(self, base_oid: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        try:
            async for indication, status, index, varbinds in bulk_cmd(
                self.engine, self.auth, await self._target(), ContextData(),
                0, 25, (ObjectName(base_oid), Null("")),
                lookupMib=False, lexicographicMode=False
            ):
                if indication:
                    raise SnmpConnectionError(str(indication))
                if status:
                    raise SnmpResponseError(
                        f"{status.prettyPrint()} at varbind index {index}"
                    )
                for oid, value in varbinds:
                    text_oid = oid.prettyPrint()
                    prefix = base_oid + "."
                    if text_oid.startswith(prefix):
                        result[text_oid[len(prefix):]] = value
        except (SnmpConnectionError, SnmpResponseError):
            raise
        except Exception as err:
            raise SnmpConnectionError(f"SNMP WALK {base_oid}: {err}") from err
        return result

    @staticmethod
    def _text(value: Any) -> str:
        return value.prettyPrint().strip()

    @staticmethod
    def _int(value: Any, label: str) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError) as err:
            raise SnmpResponseError(f"Invalid {label}: {value!r}") from err
        if number < 0:
            raise SnmpResponseError(f"Negative {label}: {number}")
        return number

    async def async_test_connection(self) -> None:
        """Test SNMP without relying on a particular storage index."""
        await self._get(SYS_DESCR_OID)

    async def async_get_storage_table(self) -> list[StorageEntry]:
        """Join the five hrStorageTable columns by SNMP index."""
        columns = await asyncio.gather(
            self._walk(HR_STORAGE_TYPE_OID),
            self._walk(HR_STORAGE_DESCR_OID),
            self._walk(HR_STORAGE_UNIT_OID),
            self._walk(HR_STORAGE_SIZE_OID),
            self._walk(HR_STORAGE_USED_OID),
        )
        types, names, units, sizes, used = columns
        rows: list[StorageEntry] = []
        for index, value in names.items():
            if any(index not in col for col in (types, units, sizes, used)):
                continue
            name = self._text(value)
            unit = self._int(units[index], f"allocation unit {index}")
            size = self._int(sizes[index], f"size {index}")
            used_value = self._int(used[index], f"used {index}")
            if not name or unit <= 0 or size <= 0:
                continue
            rows.append(StorageEntry(
                index, name, name, self._text(types[index]),
                unit, size, used_value
            ))

        # Duplicate descriptions need distinct internal selection keys.
        grouped: dict[str, list[StorageEntry]] = {}
        for row in rows:
            grouped.setdefault(row.name, []).append(row)
        output: list[StorageEntry] = []
        for name, group in grouped.items():
            group.sort(key=lambda row: row.index)
            for number, row in enumerate(group, 1):
                key = name if len(group) == 1 else f"{name}#{number}"
                output.append(StorageEntry(
                    row.index, key, row.name, row.storage_type,
                    row.allocation_unit, row.size, row.used
                ))
        return output

    async def async_get_storage(self) -> dict[str, StorageEntry]:
        rows = await self.async_get_storage_table()
        return {r.key: r for r in rows if r.storage_type == HR_STORAGE_FIXED_DISK}

    async def async_get_memory(self) -> dict[str, float] | None:
        rows = await self.async_get_storage_table()
        ram_rows = [r for r in rows if r.storage_type == HR_STORAGE_RAM]
        if not ram_rows:
            return None
        ram = max(ram_rows, key=lambda row: row.size_bytes)
        return {
            "size_gb": ram.size_bytes / 1024**3,
            "used_gb": ram.used_bytes / 1024**3,
            "percentage": ram.used / ram.size * 100,
        }
