"""Constants for the Power Watchdog integration."""

DOMAIN = "hughes_power_watchdog"

# -- Gen2 BLE GATT -----------------------------------------------------------
CHARACTERISTIC_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"
HANDSHAKE_PAYLOAD = bytes.fromhex("212521252c70726f746f636f6c2c6f70656e2c")

# -- Gen1 BLE GATT -----------------------------------------------------------
GEN1_TX_UUID = "0000ffe2-0000-1000-8000-00805f9b34fb"  # notify (device → host)
GEN1_RX_UUID = "0000fff5-0000-1000-8000-00805f9b34fb"  # write  (host → device)

# -- Gen2 packet framing -----------------------------------------------------
PACKET_IDENTIFIER = 0x24797740
PACKET_TAIL = 0x7121
HEADER_SIZE = 9
TAIL_SIZE = 2
MAX_BUFFER_SIZE = 8192

# -- Gen1 packet framing -----------------------------------------------------
GEN1_CHUNK_SIZE = 20
GEN1_MERGED_SIZE = 40
GEN1_HEADER = bytes([0x01, 0x03, 0x20])

# -- Command IDs (Gen2) ------------------------------------------------------
CMD_DL_REPORT = 1
CMD_ERROR_REPORT = 2
CMD_ALARM = 14

# -- DLData layout (Gen2) ----------------------------------------------------
DL_DATA_SIZE = 34

# -- Pre-built command packets (Gen2) ----------------------------------------
CMD_RESET_ENERGY = "2479774001060300007121"

# -- Config-flow keys --------------------------------------------------------
CONF_DEVICE_NAME = "device_name"   # friendly name chosen by the user
CONF_BLE_NAME    = "ble_name"      # raw BLE advertisement name e.g. "WD_V6_4af6ee9d9d05"

# -- BLE advertisement prefixes used during discovery ------------------------
GEN2_PREFIX = "WD_"
GEN1_PREFIX = "PM"
DEVICE_NAME_PREFIXES = (GEN2_PREFIX, GEN1_PREFIX)

# -- Gen2 suffix digit -> line count -----------------------------------------
GEN2_SINGLE_LINE_DIGITS = {"5", "6"}       # 30A
GEN2_DUAL_LINE_DIGITS   = {"7", "8", "9"}  # 50A

# -- Gen1 name prefix -> line count ------------------------------------------
GEN1_SINGLE_PREFIX = "PMS"   # 30A
GEN1_DUAL_PREFIX   = "PMD"   # 50A

# -- Gen1 hardware version (encoded in BLE name at positions 15-16) ----------
GEN1_HW_VERSIONS: dict[str, int] = {"E2": 1, "E3": 2, "E4": 3}

# -- Error code map ----------------------------------------------------------
# Gen1: byte 19 of 40-byte telemetry buffer (v2/v3 only). Codes 0-9, 11-12.
# Gen2: byte 32 of each 34-byte DLData block.        Codes 0-9, 11-14.
# Code 10 is reserved / unused in both generations.
ERROR_CODES: dict[int, tuple[str, str]] = {
    0:  ("OK",  "No error"),
    1:  ("E1",  "Line 1 voltage error - voltage above 132V or below 104V"),
    2:  ("E2",  "Line 2 voltage error - voltage above 132V or below 104V"),
    3:  ("E3",  "Line 1 overcurrent - amp draw exceeds rated limit"),
    4:  ("E4",  "Line 2 overcurrent - amp draw exceeds rated limit"),
    5:  ("E5",  "Line 1 neutral reversed - hot and neutral wires are reversed"),
    6:  ("E6",  "Line 2 neutral reversed - hot and neutral wires are reversed"),
    7:  ("E7",  "Missing ground - no ground connection detected"),
    8:  ("E8",  "Missing neutral - no neutral circuit detected"),
    9:  ("E9",  "Surge protection used up - surge board needs replacement"),
    11: ("F1",  "Line 1 frequency error - frequency out of specification"),
    12: ("F2",  "Line 2 frequency error - frequency out of specification"),
    13: ("E13", "Gen2-specific error condition"),
    14: ("E14", "Gen2-specific error condition"),
}


def error_code_display(code: int | None) -> str:
    """Return the short display code (e.g. 'E3', 'OK') for a given error code.

    Falls back to the raw numeric string for any unmapped code rather than
    fabricating an 'E{code}' label which could be misleading.
    """
    if code is None:
        return "Unknown"
    entry = ERROR_CODES.get(code)
    if entry is not None:
        return entry[0]
    return str(code)


def error_description(code: int | None) -> str:
    """Return the full description for a given error code int."""
    if code is None:
        return "Unknown"
    entry = ERROR_CODES.get(code)
    if entry is not None:
        return entry[1]
    return f"Unknown error code {code}"


def detect_line_count(ble_name: str) -> str:
    """Detect the line count from the raw BLE advertisement name.

    Returns one of three strings:
      "single"  - confirmed 30A single-line (e.g. WD_V6_..., PMS...)
      "dual"    - confirmed 50A dual-line   (e.g. WD_E7_..., PMD...)
      "unknown" - format not recognised; caller should enable everything
                  so the user can see all sensors and decide.

    IMPORTANT: pass the raw BLE advertisement name (stored as CONF_BLE_NAME),
    NOT the user-supplied friendly name (CONF_DEVICE_NAME).
    """
    if ble_name.startswith(GEN2_PREFIX):
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
