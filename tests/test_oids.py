"""OID definition tests."""
from custom_components.snmp_storage_monitor.const import (
    HR_STORAGE_TYPE_OID, HR_STORAGE_DESCR_OID, HR_STORAGE_UNIT_OID,
    HR_STORAGE_SIZE_OID, HR_STORAGE_USED_OID, HR_STORAGE_RAM,
    HR_STORAGE_FIXED_DISK, SYS_DESCR_OID,
)


def test_hr_storage_column_oids():
    assert HR_STORAGE_TYPE_OID == "1.3.6.1.2.1.25.2.3.1.2"
    assert HR_STORAGE_DESCR_OID == "1.3.6.1.2.1.25.2.3.1.3"
    assert HR_STORAGE_UNIT_OID == "1.3.6.1.2.1.25.2.3.1.4"
    assert HR_STORAGE_SIZE_OID == "1.3.6.1.2.1.25.2.3.1.5"
    assert HR_STORAGE_USED_OID == "1.3.6.1.2.1.25.2.3.1.6"


def test_storage_types_and_connectivity_oid():
    assert HR_STORAGE_RAM == "1.3.6.1.2.1.25.2.1.2"
    assert HR_STORAGE_FIXED_DISK == "1.3.6.1.2.1.25.2.1.4"
    assert SYS_DESCR_OID == "1.3.6.1.2.1.1.1.0"
