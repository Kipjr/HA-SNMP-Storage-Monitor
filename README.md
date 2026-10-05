# HA-SNMP-Storage-Monitor
Home Assistant custom integration for monitoring memory and disk storage over SNMP.

## Features

- UI-based config flow.
- First setup asks for FQDN/host, UDP port, community and polling interval.
- Walks `HOST-RESOURCES-MIB::hrStorageTable`.
- Discovers disk names dynamically.
- Disk Home Assistant entities are keyed by the disk name, not the SNMP table index.
- If the SNMP index changes, the existing entity follows the disk name.
- Explicit sensor selection during setup and reconfiguration.
- Each selected disk is one Home Assistant sensor named exactly after the SNMP disk name.
- Its state is `used / size * 100` in percent; `size_gb` and `used_gb` are state attributes.
- Memory uses the two OIDs supplied by the integration configuration.

## SNMP OIDs

Memory:
- size: `1.3.6.1.2.1.25.2.3.1.5.1`
- used: `1.3.6.1.2.1.25.2.3.1.5.11`

Disks:
- name: `1.3.6.1.2.1.25.2.3.1.3.n`
- used: `1.3.6.1.2.1.25.2.3.1.6.n`
- size: `1.3.6.1.2.1.25.2.3.1.5.n`

The integration also walks allocation units (`1.3.6.1.2.1.25.2.3.1.4.n`) so disk size can correctly convert the HOST-RESOURCES-MIB size value to bytes before converting to GB.

## HACS

Add the GitHub repository as a custom repository in HACS, category **Integration**.
