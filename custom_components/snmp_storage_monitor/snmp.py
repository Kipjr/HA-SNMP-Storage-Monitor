"""Async SNMP client using Home Assistant's shared SNMP engine."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ObjectIdentity,
    ObjectType,
    UdpTransportTarget,
    UsmUserData,
    get_cmd,
    walk_cmd,
)

from homeassistant.components.snmp.const import MAP_AUTH_PROTOCOLS, MAP_PRIV_PROTOCOLS
from homeassistant.components.snmp.util import async_create_command_cmd_args
from homeassistant.core import HomeAssistant

from .const import (
    CONF_AUTH_KEY,
    CONF_AUTH_PROTOCOL,
    CONF_COMMUNITY,
    CONF_HOST,
    CONF_PORT,
    CONF_PRIV_KEY,
    CONF_PRIV_PROTOCOL,
    CONF_USERNAME,
    CONF_VERSION,
    HR_STORAGE_DESCR_OID,
    HR_STORAGE_FIXED_DISK,
    HR_STORAGE_RAM,
    HR_STORAGE_SIZE_OID,
    HR_STORAGE_TYPE_OID,
    HR_STORAGE_UNIT_OID,
    HR_STORAGE_USED_OID,
    SNMP_VERSIONS,
    SYS_NAME_OID,
)
from .exceptions import SnmpConnectionError, SnmpMonitorError, SnmpResponseError

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StorageEntry:
    """Storage row. Index is transport metadata only."""

    index: str
    identity: str
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
    """Async SNMP v1/v2c/v3 client."""

    def __init__(self, hass: HomeAssistant, data: dict[str, Any]) -> None:
        self.hass = hass
        self.host = data[CONF_HOST]
        self.port = data[CONF_PORT]
        self.version = data[CONF_VERSION]
        _LOGGER.debug("SNMP client initialized: host=%s port=%s version=%s", self.host, self.port, self.version)

        if self.version == "3":
            from pysnmp.hlapi.v3arch import asyncio as hlapi

            auth_protocol = data.get(CONF_AUTH_PROTOCOL, "none")
            priv_protocol = data.get(CONF_PRIV_PROTOCOL, "none")
            self.auth_data = UsmUserData(
                data[CONF_USERNAME],
                data.get(CONF_AUTH_KEY) or None,
                data.get(CONF_PRIV_KEY) or None,
                authProtocol=getattr(hlapi, MAP_AUTH_PROTOCOLS[auth_protocol]),
                privProtocol=getattr(hlapi, MAP_PRIV_PROTOCOLS[priv_protocol]),
            )
        else:
            self.auth_data = CommunityData(
                data[CONF_COMMUNITY],
                mpModel=SNMP_VERSIONS[self.version],
            )

    async def _args(self):
        """Build command arguments with Home Assistant's shared engine."""
        try:
            _LOGGER.debug("Creating SNMP transport target: host=%s port=%s", self.host, self.port)
            target = await UdpTransportTarget.create(
                (self.host, self.port), timeout=8, retries=1
            )
            args = await async_create_command_cmd_args(
                self.hass, self.auth_data, target
            )
            _LOGGER.debug("SNMP transport target ready: host=%s port=%s", self.host, self.port)
            return args
        except Exception as err:
            raise SnmpConnectionError("Unable to create SNMP target") from err

    async def async_get(self, oid: str):
        """Read one OID."""
        _LOGGER.debug("SNMP GET started: host=%s oid=%s", self.host, oid)
        try:
            indication, status, index, values = await get_cmd(
                *await self._args(), ObjectType(ObjectIdentity(oid))
            )
        except Exception as err:
            raise SnmpConnectionError(f"SNMP GET failed for {oid}") from err

        if indication:
            raise SnmpConnectionError(str(indication))
        if status:
            raise SnmpResponseError(f"{status.prettyPrint()} at varbind {index}")
        if not values:
            raise SnmpResponseError(f"No response for {oid}")
        _LOGGER.debug("SNMP GET completed: host=%s oid=%s", self.host, oid)
        return values[0][1]

    async def async_walk(self, base: str) -> list[tuple[str, str]]:
        """Walk an SNMP subtree and return OID/value pairs."""
        _LOGGER.debug(
            "SNMP WALK started: host=%s oid=%s",
            self.host,
            base,
        )
    
        results: list[tuple[str, str]] = []
    
        try:
            async for indication, status, index, varbinds in walk_cmd(
                *await self._args(),
                ObjectType(ObjectIdentity(base)),
                lexicographicMode=False,
            ):
                if indication:
                    raise SnmpConnectionError(
                        f"SNMP WALK failed: {indication}"
                    )
    
                if status:
                    raise SnmpConnectionError(
                        f"SNMP WALK error: {status.prettyPrint()} at index {index}"
                    )
    
                for oid, value in varbinds:
                    if not self._has_snmp_value(value):
                        continue
    
                    results.append(
                        (oid.prettyPrint(), value.prettyPrint())
                    )
    
            _LOGGER.debug(
                "SNMP WALK completed: host=%s oid=%s entries=%d",
                self.host,
                base,
                len(results),
            )
    
            return results
    
        except SnmpMonitorError:
            raise
        except Exception as err:
            _LOGGER.exception(
                "SNMP WALK failed: host=%s oid=%s",
                self.host,
                base,
            )
            raise SnmpConnectionError(
                f"SNMP WALK failed for {base}"
            ) from err

    @staticmethod
    def _has_snmp_value(value: Any) -> bool:
        """Return false for SNMP exception values such as noSuchObject."""
        rendered = value.prettyPrint().strip().lower()
        return bool(rendered) and not rendered.startswith(
            ("no such", "end of mib")
        )

    async def async_test_permissions(self) -> tuple[bool, bool]:
        """Probe sysName and hrStorageDescr independently."""
        sysname_ok = False
        storage_ok = False

        try:
            sysname_ok = self._has_snmp_value(await self.async_get(SYS_NAME_OID))
        except SnmpMonitorError as err:
            _LOGGER.debug("SNMP sysName probe failed on %s: %s", self.host, err)

        try:
            descriptions = await self.async_walk(HR_STORAGE_DESCR_OID)
            storage_ok = bool(descriptions)
        except SnmpMonitorError as err:
            _LOGGER.debug("SNMP hrStorageDescr probe failed on %s: %s", self.host, err)

        _LOGGER.debug("SNMP permission results: host=%s sysName=%s hrStorageDescr=%s", self.host, sysname_ok, storage_ok)
        return sysname_ok, storage_ok

    async def async_test_connection(self) -> None:
        """Require the storage table to be readable."""
        sysname_ok, storage_ok = await self.async_test_permissions()
        if sysname_ok and not storage_ok:
            raise SnmpResponseError(
                "SNMP agent is reachable, but hrStorageDescr is not readable"
            )
        if not sysname_ok and not storage_ok:
            raise SnmpConnectionError(
                "Neither sysName nor hrStorageDescr is readable"
            )

    async def async_get_storage_table(self) -> list[StorageEntry]:
        """Read and join HOST-RESOURCES-MIB storage table columns."""
        types, descriptions, units, sizes, used = await asyncio.gather(
            self.async_walk(HR_STORAGE_TYPE_OID),
            self.async_walk(HR_STORAGE_DESCR_OID),
            self.async_walk(HR_STORAGE_UNIT_OID),
            self.async_walk(HR_STORAGE_SIZE_OID),
            self.async_walk(HR_STORAGE_USED_OID),
        )

        types = self._walk_to_dict(types)
        descriptions = self._walk_to_dict(descriptions)
        units = self._walk_to_dict(units)
        sizes = self._walk_to_dict(sizes)
        used = self._walk_to_dict(used)
        rows: list[StorageEntry] = []

        for index, description in descriptions.items():
            if not all(index in column for column in (types, units, sizes, used)):
                continue

            name = description.strip()
            try:
                unit = int(units[index])
                size = int(sizes[index])
                used_count = int(used[index])
            except (TypeError, ValueError) as err:
                raise SnmpResponseError(
                    "Invalid numeric value in hrStorageTable"
                ) from err

            if not name or unit <= 0 or size <= 0:
                continue

            rows.append(
                StorageEntry(
                    index=index,
                    identity=name,
                    name=name,
                    storage_type=types[index],
                    unit=unit,
                    size=size,
                    used=used_count,
                )
            )

        _LOGGER.debug("SNMP storage table parsed: host=%s rows=%d", self.host, len(rows))
        identities = [row.identity for row in rows]
        if len(identities) != len(set(identities)):
            raise SnmpResponseError(
                "Duplicate hrStorageDescr values; stable identity is ambiguous"
            )
        return rows

    def _walk_to_dict(self, rows: list[tuple[str, str]]) -> dict[int, str]:
        """Convert SNMP WALK results into an index/value dictionary."""
        result = {}
        for oid, value in rows:
            index = int(oid.rsplit(".", 1)[-1])
            result[index] = value
        return result
