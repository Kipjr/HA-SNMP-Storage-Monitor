# HA-SNMP-Storage-Monitor

Home Assistant custom integration for monitoring memory and fixed disks over SNMP.

## Features
- SNMP v1, v2c and v3 configuration.
- v1/v2c community credentials.
- v3 username, authentication protocol/key and privacy protocol/key.
- Dynamic memory and fixed-disk discovery through HOST-RESOURCES-MIB.
- User selection of discovered sensors.
- Async SNMP calls using Home Assistant's SNMP v3arch API and shared engine.
- Storage values converted using hrStorageAllocationUnits.

## Disk identity
HOST-RESOURCES-MIB does not define a universal disk GUID or device path. This integration uses hrStorageDescr as its portable identity and never uses the SNMP row index as an entity identifier. Duplicate descriptions are rejected because they cannot be uniquely and reliably identified using the standard MIB alone. A vendor-specific MIB is required to expose a disk GUID or physical path where hrStorageDescr does not contain one.

The SNMP row index is used only to join columns within one table response. It is not included in entity unique IDs.

## SNMPv3 protocols
Authentication: none, hmac-md5, hmac-sha, hmac128-sha224, hmac192-sha256, hmac256-sha384, hmac384-sha512.
Privacy: none, des, 3des-ede, aes-cfb-128, aes-cfb-192, aes-cfb-256.

The integration imports Home Assistant's internal SNMP utility to reuse its shared engine. This is not a public extension API and may require updates when Home Assistant changes its SNMP implementation.

## Storage calculations
hrStorageSize and hrStorageUsed are allocation-unit counts. Both are multiplied by hrStorageAllocationUnits before conversion to GiB. Memory rows are identified by hrStorageRam; disk rows by hrStorageFixedDisk.
