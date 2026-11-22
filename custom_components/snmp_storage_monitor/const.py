"""Integration constants."""

DOMAIN = "snmp_storage_monitor"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_VERSION = "version"
CONF_COMMUNITY = "community"
CONF_USERNAME = "username"
CONF_AUTH_PROTOCOL = "auth_protocol"
CONF_AUTH_KEY = "auth_key"
CONF_PRIV_PROTOCOL = "priv_protocol"
CONF_PRIV_KEY = "priv_key"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ENABLED_SENSORS = "enabled_sensors"
CONF_DISKS_SEPARATE_DEVICE = "disks_separate_device"

DEFAULT_PORT = 161
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 3600

MEMORY_KEY = "memory"
DISK_PREFIX = "disk:"

SYS_NAME_OID = "1.3.6.1.2.1.1.5.0"
SYS_DESCR_OID = "1.3.6.1.2.1.1.1.0"
HR_STORAGE_TYPE_OID = "1.3.6.1.2.1.25.2.3.1.2"
HR_STORAGE_DESCR_OID = "1.3.6.1.2.1.25.2.3.1.3"
HR_STORAGE_UNIT_OID = "1.3.6.1.2.1.25.2.3.1.4"
HR_STORAGE_SIZE_OID = "1.3.6.1.2.1.25.2.3.1.5"
HR_STORAGE_USED_OID = "1.3.6.1.2.1.25.2.3.1.6"
HR_STORAGE_RAM = "1.3.6.1.2.1.25.2.1.2"
HR_STORAGE_FIXED_DISK = "1.3.6.1.2.1.25.2.1.4"

SNMP_VERSIONS = {"1": 0, "2c": 1, "3": None}

AUTH_PROTOCOLS = (
    "none",
    "hmac-md5",
    "hmac-sha",
    "hmac128-sha224",
    "hmac192-sha256",
    "hmac256-sha384",
    "hmac384-sha512",
)
PRIV_PROTOCOLS = (
    "none",
    "des",
    "3des-ede",
    "aes-cfb-128",
    "aes-cfb-192",
    "aes-cfb-256",
)
