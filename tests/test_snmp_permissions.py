"""Tests for independent SNMP permission probes."""

from unittest.mock import AsyncMock

import pytest

from custom_components.snmp_storage_monitor.exceptions import SnmpResponseError
from custom_components.snmp_storage_monitor.snmp import SnmpClient


# PySNMP exposes this method name as part of its value object interface.
# pylint: disable=too-few-public-methods
class FakeValue:
    """Small stand-in for a PySNMP value."""

    def __init__(self, value: str) -> None:
        """Store the printable value."""
        self.value = value

    def prettyPrint(self) -> str:  # pylint: disable=invalid-name
        """Return the PySNMP-compatible printable value."""
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
    """Verify that GET and WALK permission probes fail independently."""
    client = object.__new__(SnmpClient)
    client.host = "test-host"

    async def fake_get(_oid: str):
        """Return a fake sysName value or simulate a failed GET."""
        if not sysname_result:
            raise SnmpResponseError("sysName unavailable")
        return FakeValue("test-host")

    async def fake_walk(_oid: str):
        """Return one WALK row or simulate a failed WALK."""
        if not storage_result:
            raise SnmpResponseError("hrStorageDescr unavailable")
        return [("1.3.6.1.2.1.25.2.3.1.3.1", "/")]

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
    """Verify that SNMP exception values are rejected."""
    assert SnmpClient._has_snmp_value(FakeValue(value)) is expected  # pylint: disable=protected-access
