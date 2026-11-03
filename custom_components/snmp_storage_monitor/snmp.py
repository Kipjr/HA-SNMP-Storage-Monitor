"""SNMP client for storage monitoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pysnmp.hlapi.v1arch.asyncio import (
    CommunityData,
    ContextData,
    SnmpEngine,
    UdpTransportTarget,
    bulk_cmd,
    get_cmd,
)
from pysnmp.proto.rfc1902 import ObjectName
from pysnmp.proto.rfc1905 import Null

from .const import (
    DISK_ALLOCATION_UNIT_OID,
    DISK_DESCR_OID,
    DISK_SIZE_OID,
    DISK_USED_OID,
    MEM_SIZE_OID,
    MEM_USED_OID,
)
from .exceptions import SnmpError


@dataclass
class StorageEntry:
    """SNMP storage table entry."""

    index: str
    name: str
    allocation_unit: int
    size: int
    used: int


class SnmpClient:
    """Asynchronous SNMP client."""

    def __init__(
        self,
        host: str,
        port: int,
        community: str,
    ) -> None:
        self.host = host
        self.port = port
        self.community = community
        self.engine = SnmpEngine()

    async def _transport(self) -> UdpTransportTarget:
        """Create the UDP transport target."""
        return await UdpTransportTarget.create(
            (self.host, self.port),
            timeout=5,
            retries=1,
        )

    @staticmethod
    def _raw_oid(oid: str) -> ObjectName:
        """Convert a numeric OID to an SNMP ObjectName."""
        return ObjectName(oid)

    async def _get(self, oid: str) -> Any:
        """Read one OID without loading MIB files."""
        transport = await self._transport()

        error_indication, error_status, error_index, var_binds = await get_cmd(
            self.engine,
            CommunityData(self.community, mpModel=1),
            transport,
            ContextData(),
            (self._raw_oid(oid), Null("")),
            lookupMib=False,
        )

        if error_indication:
            raise SnmpError(str(error_indication))

        if error_status:
            raise SnmpError(
                f"{error_status.prettyPrint()} at index {error_index}"
            )

        if not var_binds:
            raise SnmpError(f"No response for OID {oid}")

        return var_binds[0][1]

    async def _walk(self, base_oid: str) -> dict[str, Any]:
        """Walk an OID subtree without loading MIB files."""
        transport = await self._transport()

        results: dict[str, Any] = {}

        async for (
            error_indication,
            error_status,
            error_index,
            var_binds,
        ) in bulk_cmd(
            self.engine,
            CommunityData(self.community, mpModel=1),
            transport,
            ContextData(),
            0,
            25,
            (self._raw_oid(base_oid), Null("")),
            lookupMib=False,
            lexicographicMode=False,
        ):
            if error_indication:
                raise SnmpError(str(error_indication))

            if error_status:
                raise SnmpError(
                    f"{error_status.prettyPrint()} at index {error_index}"
                )

            for oid, value in var_binds:
                oid_string = oid.prettyPrint()

                if not oid_string.startswith(f"{base_oid}."):
                    continue

                index = oid_string[len(base_oid) + 1:]
                results[index] = value

        return results

    async def async_test_connection(self) -> None:
        """Test the SNMP connection."""
        await self._get(MEM_SIZE_OID)

    async def async_get_memory(self) -> dict[str, float]:
        """Read memory values."""
        size_raw = await self._get(MEM_SIZE_OID)
        used_raw = await self._get(MEM_USED_OID)

        size_bytes = int(size_raw)
        used_bytes = int(used_raw)

        if size_bytes <= 0:
            raise SnmpError("Invalid memory size returned by SNMP")

        return {
            "size_gb": size_bytes / (1024 ** 3),
            "used_gb": used_bytes / (1024 ** 3),
            "percentage": used_bytes / size_bytes * 100,
        }

    async def async_get_storage(self) -> dict[str, StorageEntry]:
        """Read storage table entries."""
        names = await self._walk(DISK_DESCR_OID)
        sizes = await self._walk(DISK_SIZE_OID)
        used_values = await self._walk(DISK_USED_OID)
        allocation_units = await self._walk(DISK_ALLOCATION_UNIT_OID)

        storage: dict[str, StorageEntry] = {}

        for index, name_value in names.items():
            if (
                index not in sizes
                or index not in used_values
                or index not in allocation_units
            ):
                continue

            name = str(name_value.prettyPrint()).strip()

            if not name:
                continue

            storage[name] = StorageEntry(
                index=index,
                name=name,
                allocation_unit=int(allocation_units[index]),
                size=int(sizes[index]),
                used=int(used_values[index]),
            )

        return storage
