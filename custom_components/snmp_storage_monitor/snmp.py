"""Async SNMP client using Home Assistant's shared SNMP engine."""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from pysnmp.hlapi.v3arch.asyncio import CommunityData, UsmUserData, UdpTransportTarget, get_cmd, bulk_cmd, ObjectType, ObjectIdentity
from homeassistant.components.snmp.const import MAP_AUTH_PROTOCOLS, MAP_PRIV_PROTOCOLS, SNMP_VERSIONS
from homeassistant.components.snmp.util import async_create_command_cmd_args
from homeassistant.core import HomeAssistant
from .const import *
from .exceptions import SnmpConnectionError, SnmpResponseError

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
    def size_bytes(self): return self.allocation_unit * self.size
    @property
    def used_bytes(self): return self.allocation_unit * self.used

class SnmpClient:
    """Async SNMP v1/v2c/v3 client."""
    def __init__(self, hass: HomeAssistant, data: dict[str, Any]):
        self.hass = hass
        self.host, self.port, self.version = data[CONF_HOST], data[CONF_PORT], data[CONF_VERSION]
        if self.version == "3":
            from pysnmp.hlapi.v3arch import asyncio as hlapi
            auth = getattr(hlapi, MAP_AUTH_PROTOCOLS[data.get(CONF_AUTH_PROTOCOL, "none")])
            priv = getattr(hlapi, MAP_PRIV_PROTOCOLS[data.get(CONF_PRIV_PROTOCOL, "none")])
            self.auth_data = UsmUserData(data[CONF_USERNAME], data.get(CONF_AUTH_KEY) or None,
                data.get(CONF_PRIV_KEY) or None, authProtocol=auth, privProtocol=priv)
        else:
            self.auth_data = CommunityData(data[CONF_COMMUNITY], mpModel=SNMP_VERSIONS[self.version])

    async def _args(self):
        try:
            target = await UdpTransportTarget.create((self.host, self.port), timeout=8, retries=1)
            return await async_create_command_cmd_args(self.hass, self.auth_data, target)
        except Exception as err:
            raise SnmpConnectionError("Unable to create SNMP target") from err

    async def async_get(self, oid: str):
        try:
            indication, status, index, values = await get_cmd(*await self._args(), ObjectType(ObjectIdentity(oid)))
        except Exception as err:
            raise SnmpConnectionError(f"SNMP GET failed for {oid}") from err
        if indication: raise SnmpConnectionError(str(indication))
        if status: raise SnmpResponseError(f"{status.prettyPrint()} at varbind {index}")
        if not values: raise SnmpResponseError(f"No response for {oid}")
        return values[0][1]

    async def async_walk(self, base: str):
        found = {}
        try:
            async for indication, status, index, varbinds in bulk_cmd(
                *await self._args(), 0, 25, ObjectType(ObjectIdentity(base)), lexicographicMode=False
            ):
                if indication: raise SnmpConnectionError(str(indication))
                if status: raise SnmpResponseError(f"{status.prettyPrint()} at varbind {index}")
                for oid, value in varbinds:
                    text_oid = oid.prettyPrint()
                    if text_oid.startswith(base + "."):
                        found[text_oid[len(base) + 1:]] = value
        except (SnmpConnectionError, SnmpResponseError): raise
        except Exception as err: raise SnmpConnectionError(f"SNMP WALK failed for {base}") from err
        return found

    @staticmethod
    def _has_snmp_value(value):
        """Return false for SNMP exception values such as noSuchObject."""
        rendered = value.prettyPrint().strip().lower()
        return bool(rendered) and not rendered.startswith(("no such", "end of mib"))

    async def async_test_permissions(self):
        """Probe sysName and hrStorageDescr independently.

        A readable sysName without readable storage data indicates that the
        agent is reachable but the configured SNMP user lacks storage access.
        """
        sysname_ok = False
        storage_ok = False

        try:
            sysname_ok = self._has_snmp_value(await self.async_get(SYS_NAME_OID))
        except SnmpMonitorError as err:
            _LOGGER.debug("SNMP sysName probe failed on %s: %s", self.host, err)

        try:
            descriptions = await self.async_walk(HR_STORAGE_DESCR_OID)
            storage_ok = bool(descriptions) and any(
                self._has_snmp_value(value) for value in descriptions.values()
            )
        except SnmpMonitorError as err:
            _LOGGER.debug("SNMP hrStorageDescr probe failed on %s: %s", self.host, err)

        return sysname_ok, storage_ok

    async def async_test_connection(self):
        """Compatibility wrapper: require the storage table to be readable."""
        sysname_ok, storage_ok = await self.async_test_permissions()
        if sysname_ok and not storage_ok:
            raise SnmpResponseError("SNMP agent is reachable, but hrStorageDescr is not readable")
        if not sysname_ok and not storage_ok:
            raise SnmpConnectionError("Neither sysName nor hrStorageDescr is readable")

    async def async_get_storage_table(self):
        columns = await asyncio.gather(
            self.async_walk(HR_STORAGE_TYPE_OID), self.async_walk(HR_STORAGE_DESCR_OID),
            self.async_walk(HR_STORAGE_UNIT_OID), self.async_walk(HR_STORAGE_SIZE_OID),
            self.async_walk(HR_STORAGE_USED_OID))
        types, descriptions, units, sizes, used = columns
        rows = []
        for index, desc in descriptions.items():
            if not all(index in col for col in (types, units, sizes, used)): continue
            name = desc.prettyPrint().strip()
            try:
                unit, size, used_count = int(units[index]), int(sizes[index]), int(used[index])
            except (TypeError, ValueError) as err:
                raise SnmpResponseError("Invalid numeric value in hrStorageTable") from err
            if not name or unit <= 0 or size <= 0: continue
            rows.append(StorageEntry(index, name, name, types[index].prettyPrint(), unit, size, used_count))
        identities = [r.identity for r in rows]
        if len(identities) != len(set(identities)):
            raise SnmpResponseError("Duplicate hrStorageDescr values; stable identity is ambiguous")
        return rows
