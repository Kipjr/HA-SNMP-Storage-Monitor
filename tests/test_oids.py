"""Basic tests for OID configuration."""

from custom_components.snmp_storage_monitor.const import (
    HR_STORAGE_DESCR_OID,
    HR_STORAGE_SIZE_OID,
    HR_STORAGE_USED_OID,
    MEM_SIZE_OID,
    MEM_USED_OID,
)


def test_oids() -> None:
    assert MEM_SIZE_OID == "1.3.6.1.2.1.25.2.3.1.5.1"
    assert MEM_USED_OID == "1.3.6.1.2.1.25.2.3.1.5.11"
    assert HR_STORAGE_DESCR_OID == "1.3.6.1.2.1.25.2.3.1.3"
    assert HR_STORAGE_USED_OID == "1.3.6.1.2.1.25.2.3.1.6"
    assert HR_STORAGE_SIZE_OID == "1.3.6.1.2.1.25.2.3.1.5"
