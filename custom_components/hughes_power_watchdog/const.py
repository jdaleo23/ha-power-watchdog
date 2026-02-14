"""Constants for the Power Watchdog integration."""

DOMAIN = "hughes_power_watchdog"

# ── BLE GATT ────────────────────────────────────────────────────────────────
# Service UUID 000000ff, characteristic UUID 0000ff01 (same for notify & write)
CHARACTERISTIC_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"

# ASCII "!%!%,protocol,open," — sent after subscribing to start data flow
HANDSHAKE_PAYLOAD = bytes.fromhex("212521252c70726f746f636f6c2c6f70656e2c")

# ── Packet framing ──────────────────────────────────────────────────────────
# Every packet starts with a 4-byte identifier and ends with a 2-byte tail.
# Notifications may be fragmented across multiple BLE callbacks; a reassembly
# buffer accumulates bytes until a complete packet can be extracted.
PACKET_IDENTIFIER = 0x24797740
PACKET_TAIL = 0x7121
HEADER_SIZE = 9   # 4 (identifier) + 1 (version) + 1 (msgId) + 1 (cmd) + 2 (dataLen)
TAIL_SIZE = 2
MAX_BUFFER_SIZE = 8192

# ── Command IDs (byte 6 of each packet) ────────────────────────────────────
CMD_DL_REPORT = 1       # Power data — the primary telemetry frame
CMD_ERROR_REPORT = 2    # Fault / error history
CMD_ALARM = 14          # Surge or fault alarm

# ── DLData layout ───────────────────────────────────────────────────────────
# Each AC line is represented by a 34-byte DLData block inside a DLReport.
#   30A models send 34 bytes (one line).
#   50A models send 68 bytes (L1 followed by L2).
DL_DATA_SIZE = 34

# ── Pre-built command packets ───────────────────────────────────────────────
CMD_RESET_ENERGY = "2479774001060300007121"

# ── Config-flow keys ────────────────────────────────────────────────────────
CONF_DEVICE_NAME = "device_name"

# ── BLE advertisement prefixes used during discovery ────────────────────────
DEVICE_NAME_PREFIXES = ("WD_V6", "WD_E7", "WD_E8")
