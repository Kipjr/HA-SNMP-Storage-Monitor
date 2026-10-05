"""Constants for SNMP Storage Monitor."""

from typing import Final

DOMAIN: Final = "snmp_storage_monitor"
PLATFORM: Final = "sensor"

CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_COMMUNITY: Final = "community"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_ENABLED_SENSORS: Final = "enabled_sensors"

DEFAULT_PORT: Final = 161
DEFAULT_COMMUNITY: Final = "public"
DEFAULT_SCAN_INTERVAL: Final = 60

MEMORY_KEY: Final = "memory"
DISK_PREFIX: Final = "disk:"

HR_STORAGE_DESCR_OID: Final = "1.3.6.1.2.1.25.2.3.1.3"
HR_STORAGE_SIZE_OID: Final = "1.3.6.1.2.1.25.2.3.1.5"
HR_STORAGE_USED_OID: Final = "1.3.6.1.2.1.25.2.3.1.6"
HR_STORAGE_UNIT_OID: Final = "1.3.6.1.2.1.25.2.3.1.4"

MEM_SIZE_OID: Final = "1.3.6.1.2.1.25.2.3.1.5.1"
MEM_USED_OID: Final = "1.3.6.1.2.1.25.2.3.1.5.11"

MIN_SCAN_INTERVAL: Final = 30
MAX_SCAN_INTERVAL: Final = 3600
