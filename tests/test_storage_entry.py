"""Tests for storage row calculations and identity rules."""

from custom_components.snmp_storage_monitor.snmp import StorageEntry


def test_storage_values_use_allocation_units() -> None:
    """Verify that storage sizes use the reported allocation unit."""
    row = StorageEntry("7", "/data", "/data", "1.3.6.1.2.1.25.2.1.4", 4096, 100, 25)
    assert row.size_bytes == 409600
    assert row.used_bytes == 102400


def test_identity_is_independent_from_snmp_index() -> None:
    """Verify that storage identity remains stable when the SNMP index changes."""
    first = StorageEntry("7", "/data", "/data", "disk", 4096, 100, 25)
    after_reindex = StorageEntry("19", "/data", "/data", "disk", 4096, 100, 25)
    assert first.identity == after_reindex.identity
