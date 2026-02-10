"""Constants for the Power Watchdog integration."""

DOMAIN = "hughes_power_watchdog"

# The UUIDs we found
SERVICE_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"

# The Magic Handshake we discovered
# "!%!%,protocol,open,"
HANDSHAKE_PAYLOAD = bytes.fromhex("212521252c70726f746f636f6c2c6f70656e2c")


CONF_DEVICE_NAME = "device_name"
