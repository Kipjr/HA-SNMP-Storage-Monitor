"""Integration constants."""
from typing import Final

DOMAIN: Final = "snmp_storage_monitor"
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_COMMUNITY: Final = "community"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_ENABLED_SENSORS: Final = "enabled_sensors"
DEFAULT_PORT: Final = 161
DEFAULT_COMMUNITY: Final = "public"
DEFAULT_SCAN_INTERVAL: Final = 60
MIN_SCAN_INTERVAL: Final = 30
MAX_SCAN_INTERVAL: Final = 3600
MEMORY_KEY: Final = "memory"
DISK_PREFIX: Final = "disk:"
HR_STORAGE_TYPE_OID: Final = "1.3.6.1.2.1.25.2.3.1.2"
HR_STORAGE_DESCR_OID: Final = "1.3.6.1.2.1.25.2.3.1.3"
HR_STORAGE_UNIT_OID: Final = "1.3.6.1.2.1.25.2.3.1.4"
HR_STORAGE_SIZE_OID: Final = "1.3.6.1.2.1.25.2.3.1.5"
HR_STORAGE_USED_OID: Final = "1.3.6.1.2.1.25.2.3.1.6"
HR_STORAGE_RAM: Final = "1.3.6.1.2.1.25.2.1.2"
HR_STORAGE_FIXED_DISK: Final = "1.3.6.1.2.1.25.2.1.4"
SYS_DESCR_OID: Final = "1.3.6.1.2.1.1.1.0"
