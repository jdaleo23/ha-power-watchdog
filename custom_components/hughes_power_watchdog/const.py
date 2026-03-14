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
CONF_DEVICE_NAME = "device_name"   # friendly name chosen by the user
CONF_BLE_NAME    = "ble_name"      # raw BLE advertisement name e.g. "WD_V6_4af6ee9d9d05"

# ── BLE advertisement prefixes used during discovery ────────────────────────
# Gen2 (WiFi+BT) devices advertise as "WD_{type}_{serialhex}"
#   Types: E5, E6, E7, E8, E9, V5, V6, V7, V8, V9
#   Suffix digit determines line count: 5/6 = 30A single, 7/8/9 = 50A dual
# Gen1 (BT-only) devices advertise as "PM{S|D}..." (19 chars)
#   PMS = 30A single, PMD = 50A dual
GEN2_PREFIX = "WD_"
GEN1_PREFIX = "PM"
DEVICE_NAME_PREFIXES = (GEN2_PREFIX, GEN1_PREFIX)

# ── Gen2 suffix digit → line count ──────────────────────────────────────────
GEN2_SINGLE_LINE_DIGITS = {"5", "6"}       # 30A
GEN2_DUAL_LINE_DIGITS   = {"7", "8", "9"}  # 50A

# Gen1 name prefix → line count
GEN1_SINGLE_PREFIX = "PMS"   # 30A
GEN1_DUAL_PREFIX   = "PMD"   # 50A


def detect_line_count(ble_name: str) -> str:
    """Detect the line count from the raw BLE advertisement name.

    Returns one of three strings:
      "single"  — confirmed 30A single-line (e.g. WD_V6_..., PMS...)
      "dual"    — confirmed 50A dual-line   (e.g. WD_E7_..., PMD...)
      "unknown" — format not recognised; caller should enable everything
                  so the user can see all sensors and decide.

    IMPORTANT: pass the raw BLE advertisement name (stored as CONF_BLE_NAME),
    NOT the user-supplied friendly name (CONF_DEVICE_NAME).

    Detection rules:
      Gen 2  — "WD_{letter}{digit}_{serial}": suffix digit 5/6 → single,
                                               suffix digit 7/8/9 → dual
      Gen 1  — name starts with "PMS" → single, "PMD" → dual
    """
    if ble_name.startswith(GEN2_PREFIX):
        # e.g. "WD_V6_4af6ee9d9d05" → parts[1] = "V6" → digit = "6"
        parts = ble_name.split("_")
        if len(parts) >= 2:
            type_token = parts[1]
            if len(type_token) >= 2:
                digit = type_token[-1]
                if digit in GEN2_SINGLE_LINE_DIGITS:
                    return "single"
                if digit in GEN2_DUAL_LINE_DIGITS:
                    return "dual"

    elif ble_name.startswith(GEN1_PREFIX):
        if ble_name.startswith(GEN1_DUAL_PREFIX):
            return "dual"
        if ble_name.startswith(GEN1_SINGLE_PREFIX):
            return "single"

    return "unknown"
