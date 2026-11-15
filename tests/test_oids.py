"""OID definition tests."""
from custom_components.snmp_storage_monitor.const import (
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


def test_hr_storage_column_oids() -> None:
    assert HR_STORAGE_TYPE_OID == "1.3.6.1.2.1.25.2.3.1.2"
    assert HR_STORAGE_DESCR_OID == "1.3.6.1.2.1.25.2.3.1.3"
    assert HR_STORAGE_UNIT_OID == "1.3.6.1.2.1.25.2.3.1.4"
    assert HR_STORAGE_SIZE_OID == "1.3.6.1.2.1.25.2.3.1.5"
    assert HR_STORAGE_USED_OID == "1.3.6.1.2.1.25.2.3.1.6"


def test_storage_types_and_sysname_oid() -> None:
    assert HR_STORAGE_RAM == "1.3.6.1.2.1.25.2.1.2"
    assert HR_STORAGE_FIXED_DISK == "1.3.6.1.2.1.25.2.1.4"
    assert SYS_NAME_OID == "1.3.6.1.2.1.1.5.0"


def test_snmp_version_mapping() -> None:
    assert SNMP_VERSIONS == {"1": 0, "2c": 1, "3": None}
