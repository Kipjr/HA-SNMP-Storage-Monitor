"""Exceptions for SNMP Storage Monitor."""


class SnmpMonitorError(Exception):
    """Base exception."""


class SnmpConnectionError(SnmpMonitorError):
    """Raised when the SNMP agent cannot be reached."""


class SnmpResponseError(SnmpMonitorError):
    """Raised when the SNMP agent returns an error."""
