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

# ── Error codes (byte 32 of each DLData block, range 0-14) ──────────────────
# Codes 0-9 and 11-12 are common to Gen1 and Gen2 hardware.
# Codes 13-14 are Gen2-only.  Code 10 is reserved / unused.
ERROR_CODES: dict[int, tuple[str, str]] = {
    0: (
        "No Error",
        "Normal operation.",
    ),
    1: (
        "Line 1 Voltage Error",
        "Input voltage has exceeded 132V or dropped below 104V. The Watchdog "
        "has shut off power to protect the RV. Power will be restored "
        "automatically after voltage remains in the safe range for 90 seconds.",
    ),
    2: (
        "Line 2 Voltage Error",
        "Same as code 1, but on Line 2 (50A models only).",
    ),
    3: (
        "Line 1 Over Current",
        "Current draw exceeds the rated amperage on Line 1. The park breaker "
        "should have tripped but did not. Reduce load by turning off a major "
        "appliance. Low voltage can cause higher amperage draw.",
    ),
    4: (
        "Line 2 Over Current",
        "Same as code 3, but on Line 2 (50A models only).",
    ),
    5: (
        "Line 1 Neutral Reversed",
        "Hot and neutral wires are reversed at the power source. This is a "
        "serious wiring fault that can damage appliances. The Watchdog will "
        "not allow power through until the condition is corrected. Power "
        "restores automatically after a 90-second delay once fixed.",
    ),
    6: (
        "Line 2 Neutral Reversed",
        "Same as code 5, but on Line 2 (50A models only). Once fixed, the "
        "device may require a physical unplug/replug to reset.",
    ),
    7: (
        "Missing Ground",
        "The ground connection has been lost. Without a ground, the safety "
        "breaker cannot trip if a wire contacts the RV chassis, creating a "
        "shock hazard. The Watchdog will not allow power without a ground "
        "connection. Power restores automatically after a 90-second delay "
        "once fixed.",
    ),
    8: (
        "Neutral Missing",
        "The neutral return path is absent inside the RV. Without a neutral, "
        "appliances will burn up quickly. The Watchdog will not allow power "
        "until the neutral circuit is restored.",
    ),
    9: (
        "Surge Protection Used Up",
        "The surge absorption capacity of the internal MOV board has been "
        "exhausted. The RV will continue to operate but is no longer "
        "protected against surges. The surge board should be replaced.",
    ),
    11: (
        "Line 1 Frequency Error",
        "AC frequency on Line 1 is outside the acceptable range.",
    ),
    12: (
        "Line 2 Frequency Error",
        "AC frequency on Line 2 is outside the acceptable range.",
    ),
    13: (
        "Gen2 Error 13",
        "Additional error condition. Model-specific; reported on E8/V8 "
        "50A units.",
    ),
    14: (
        "Gen2 Error 14",
        "Additional error condition. Model-specific; reported on E6/V6, "
        "E8/V8, and E5/V5 units.",
    ),
}

# ── Config-flow keys ────────────────────────────────────────────────────────
CONF_DEVICE_NAME = "device_name"

# ── BLE advertisement prefixes used during discovery ────────────────────────
# Gen2 (WiFi+BT) devices advertise as "WD_{type}_{serialhex}"
#   Types: E5, E6, E7, E8, E9, V5, V6, V7, V8, V9
#   Suffix digit determines line count: 5/6 = 30A single, 7/8/9 = 50A dual
# Gen1 (BT-only) devices advertise as "PM{S|D}..." (19 chars)
#   PMS = 30A single, PMD = 50A dual
GEN2_PREFIX = "WD_"
GEN1_PREFIX = "PM"
DEVICE_NAME_PREFIXES = (GEN2_PREFIX, GEN1_PREFIX)
