"""Tests for independent SNMP permission probes."""
from unittest.mock import AsyncMock

import pytest

from custom_components.snmp_storage_monitor.snmp import SnmpClient\nfrom custom_components.snmp_storage_monitor.exceptions import SnmpResponseError


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
    sysname_result, storage_result, expected
):
    client = object.__new__(SnmpClient)
    client.host = "test-host"

    async def fake_get(_oid):
        if not sysname_result:
            raise SnmpResponseError("sysName unavailable")
        return FakeValue("test-host")

    async def fake_walk(_oid):
        if not storage_result:
            raise SnmpResponseError("hrStorageDescr unavailable")
        return {"1": FakeValue("/")}
    
    client.async_get = AsyncMock(side_effect=fake_get)
    client.async_walk = AsyncMock(side_effect=fake_walk)

    result = await client.async_test_permissions()
    assert result == expected


class FakeValue:
    def __init__(self, value):
        self.value = value

    def prettyPrint(self):
        return self.value
