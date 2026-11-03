"""Integration exceptions."""
class SnmpMonitorError(Exception):
    """Base SNMP integration error."""

class SnmpConnectionError(SnmpMonitorError):
    """SNMP agent cannot be reached."""

class SnmpResponseError(SnmpMonitorError):
    """SNMP agent returned an invalid response."""
