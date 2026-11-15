"""Tests for independent SNMP permission probes."""
from unittest.mock import AsyncMock

import pytest

from custom_components.snmp_storage_monitor.exceptions import SnmpResponseError
from custom_components.snmp_storage_monitor.snmp import SnmpClient


class FakeValue:
    """Small stand-in for a PySNMP value."""

    def __init__(self, value: str) -> None:
        self.value = value

    def prettyPrint(self) -> str:
        return self.value


@pytest.mark.parametrize(
    ("sysname_result", "storage_result", "expected"),
    [
        (True, True, (True, True)),
        (True, False, (True, False)),
        (False, True, (False, True)),
        (False, False, (False, False)),
    ],
)
async def test_permission_probes_are_independent(
    sysname_result: bool, storage_result: bool, expected: tuple[bool, bool]
) -> None:
    client = object.__new__(SnmpClient)
    client.host = "test-host"

    async def fake_get(_oid: str):
        if not sysname_result:
            raise SnmpResponseError("sysName unavailable")
        return FakeValue("test-host")

    async def fake_walk(_oid: str):
        if not storage_result:
            raise SnmpResponseError("hrStorageDescr unavailable")
        return {"1": FakeValue("/")}

    client.async_get = AsyncMock(side_effect=fake_get)
    client.async_walk = AsyncMock(side_effect=fake_walk)

    assert await client.async_test_permissions() == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("hostname", True),
        ("No Such Object currently exists at this OID", False),
        ("No Such Instance currently exists at this OID", False),
        ("End of MIB", False),
        ("", False),
    ],
)
def test_has_snmp_value(value: str, expected: bool) -> None:
    assert SnmpClient._has_snmp_value(FakeValue(value)) is expected
