"""Small asynchronous SNMP client used by the integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pysnmp.hlapi.v1arch.asyncio import (
    CommunityData,
    ObjectIdentity,
    ObjectType,
    SnmpDispatcher,
    UdpTransportTarget,
    bulk_cmd,
    get_cmd,
)

from .const import (
    HR_STORAGE_DESCR_OID,
    HR_STORAGE_SIZE_OID,
    HR_STORAGE_UNIT_OID,
    HR_STORAGE_USED_OID,
    MEM_SIZE_OID,
    MEM_USED_OID,
)
from .exceptions import SnmpConnectionError, SnmpResponseError


@dataclass(slots=True, frozen=True)
class StorageEntry:
    """One hrStorageTable entry."""

    index: int
    name: str
    allocation_unit: int
    size: int
    used: int


class SnmpClient:
    """SNMP v2c client."""

    def __init__(self, host: str, port: int, community: str) -> None:
        self._host = host
        self._port = port
        self._community = community

    async def _target(self) -> UdpTransportTarget:
        return await UdpTransportTarget.create(
            (self._host, self._port),
            timeout=5,
            retries=1,
        )

    def _auth(self) -> CommunityData:
        return CommunityData(self._community, mpModel=1)

    async def _get(self, oid: str) -> int | str:
        dispatcher = SnmpDispatcher()
        try:
            error_indication, error_status, error_index, var_binds = await get_cmd(
                dispatcher,
                self._auth(),
                await self._target(),
                ObjectType(ObjectIdentity(oid)),
            )
        except Exception as err:
            raise SnmpConnectionError(str(err)) from err
        finally:
            dispatcher.close_dispatcher()

        if error_indication:
            raise SnmpConnectionError(str(error_indication))
        if error_status:
            raise SnmpResponseError(
                f"{error_status.prettyPrint()} at index {error_index}"
            )
        if not var_binds:
            raise SnmpResponseError(f"No value returned for {oid}")

        value = var_binds[0][1]
        if value.isSameTypeWith(value.clone(0)):
            return int(value)
        return value.prettyPrint()

    async def _walk(self, base_oid: str) -> dict[int, Any]:
        dispatcher = SnmpDispatcher()
        result: dict[int, Any] = {}
        try:
            iterator = bulk_cmd(
                dispatcher,
                self._auth(),
                await self._target(),
                0,
                25,
                ObjectType(ObjectIdentity(base_oid)),
                lexicographicMode=False,
            )
            async for error_indication, error_status, error_index, var_binds in iterator:
                if error_indication:
                    raise SnmpConnectionError(str(error_indication))
                if error_status:
                    raise SnmpResponseError(
                        f"{error_status.prettyPrint()} at index {error_index}"
                    )
                for var_bind in var_binds:
                    oid, value = var_bind
                    oid_text = str(oid)
                    prefix = base_oid + "."
                    if not oid_text.startswith(prefix):
                        return result
                    try:
                        index = int(oid_text[len(prefix):])
                    except ValueError:
                        continue
                    result[index] = value
        except (SnmpConnectionError, SnmpResponseError):
            raise
        except Exception as err:
            raise SnmpConnectionError(str(err)) from err
        finally:
            dispatcher.close_dispatcher()
        return result

    async def async_test_connection(self) -> None:
        """Validate the configured agent."""
        await self._get(MEM_SIZE_OID)

    async def async_get_memory(self) -> tuple[float, float, float]:
        """Return memory size GB, used GB and percentage.

        The supplied memory OIDs are used exactly as requested.  Their values
        are interpreted as bytes for the GB conversion.
        """
        size = float(await self._get(MEM_SIZE_OID))
        used = float(await self._get(MEM_USED_OID))
        size_gb = size / (1024**3)
        used_gb = used / (1024**3)
        percentage = (used / size * 100) if size else 0.0
        return size_gb, used_gb, percentage

    async def async_get_storage(self) -> dict[str, StorageEntry]:
        """Walk hrStorageTable and return entries keyed by their name."""
        descriptions = await self._walk(HR_STORAGE_DESCR_OID)
        sizes = await self._walk(HR_STORAGE_SIZE_OID)
        used = await self._walk(HR_STORAGE_USED_OID)
        units = await self._walk(HR_STORAGE_UNIT_OID)

        entries: dict[str, StorageEntry] = {}
        for index, description in descriptions.items():
            if index not in sizes or index not in used:
                continue

            name = description.prettyPrint()
            try:
                allocation_unit = int(units.get(index, 1))
                size = int(sizes[index])
                used_value = int(used[index])
            except (TypeError, ValueError):
                continue

            # Avoid exposing pseudo-storage rows that cannot represent a disk.
            if not name or allocation_unit <= 0 or size < 0 or used_value < 0:
                continue

            entries[name] = StorageEntry(
                index=index,
                name=name,
                allocation_unit=allocation_unit,
                size=size,
                used=used_value,
            )
        return entries
