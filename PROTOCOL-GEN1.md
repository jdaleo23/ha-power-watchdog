# Gen1 Power Watchdog BLE Protocol

Gen1 (BT-only) Power Watchdog devices use a raw Modbus-style protocol
over Nordic UART-style BLE characteristics. They advertise a BLE name
starting with `PM`, exactly 19 characters long (padded with trailing
spaces up to 27 characters).

## Device Identification

### Name Format

The BLE advertised name encodes the line type and hardware version:

```
P M S X X X X X X X X X X X X E 3 X X
0 1 2 3                       15 16
    |                          |
    line type                  hardware version code
```

| Position | Field | Values |
|----------|-------|--------|
| `name[2]` | Line type | `S` = 30A single-line, `D` = 50A dual-line |
| `name[15:17]` | Hardware version | `E2` = v1, `E3` = v2, `E4` = v3 |

### Device Models

| Name Prefix | Amperage | Line Configuration |
|-------------|----------|--------------------|
| `PMS...`    | 30A      | Single-line        |
| `PMD...`    | 50A      | Dual-line (L1+L2)  |

### Hardware Versions

Gen1 devices have three hardware revisions that affect telemetry
parsing, particularly line detection and error code availability:

| Version Code | Version | Notes |
|-------------|---------|-------|
| `E2` | v1 | Original hardware. Error code byte is unused. Line markers use `(0,0,0)` for L2. |
| `E3` | v2 | Error code at byte 19. Line markers use `(1,1,1)` for L2. |
| `E4` | v3 | Same protocol behavior as v2. |

## GATT Service

Gen1 devices use two separate characteristics under a Nordic UART-style
service, unlike Gen2 which uses a single characteristic.

| Role    | UUID                                     | Properties              |
|---------|------------------------------------------|-------------------------|
| TX (notify) | `0000ffe2-0000-1000-8000-00805f9b34fb` | Notify                  |
| RX (write)  | `0000fff5-0000-1000-8000-00805f9b34fb` | Write / Write Without Response |

- **TX** (`ffe2`): Subscribe to notifications to receive telemetry.
- **RX** (`fff5`): Available for writing, but Gen1 requires no handshake
  or commands — telemetry begins streaming immediately on subscribe.

## Connection Sequence

1. Scan for BLE devices with names matching `PM*` (19 chars after
   stripping trailing spaces)
2. Connect to the device
3. Subscribe to notifications on TX characteristic `0000ffe2`
4. Telemetry starts streaming immediately — **no handshake required**

## Telemetry Framing

Data arrives as pairs of 20-byte BLE notifications. There is no packet
framing layer — the raw bytes carry Modbus-style register data.

### Chunk Reassembly

1. **First chunk** (20 bytes): Identified by the header `01 03 20`
   in the first three bytes (Modbus slave 1, function 3
   "read holding registers", 32 data bytes).
2. **Second chunk** (20 bytes): The next notification that does not
   start with the header.
3. The two chunks are concatenated to form a **40-byte merged buffer**.

If a notification starts with `01 03 20`, it replaces any buffered
first chunk (discarding the previous one if the second chunk never
arrived). Notifications that are not exactly 20 bytes are ignored.

### 40-Byte Buffer Layout

All multi-byte integers are **big-endian unsigned 32-bit** (`uint32`),
unlike the Gen2 protocol which uses signed `int32`.

| Offset  | Size    | Type        | Field         | Unit / Scale     |
|---------|---------|-------------|---------------|------------------|
| 0–2     | 3 bytes | —           | Header        | `01 03 20`       |
| 3–6     | 4 bytes | uint32 (BE) | Voltage       | /10000 = Volts   |
| 7–10    | 4 bytes | uint32 (BE) | Current       | /10000 = Amps    |
| 11–14   | 4 bytes | uint32 (BE) | Power         | /10000 = Watts   |
| 15–18   | 4 bytes | uint32 (BE) | Energy        | /10000 = kWh     |
| 19      | 1 byte  | uint8       | Error Code    | v2/v3 only; 0 on v1 |
| 20–30   | 11 bytes| —           | (unused)      |                  |
| 31–34   | 4 bytes | uint32 (BE) | Frequency     | /100 = Hz        |
| 35–36   | 2 bytes | —           | (unused)      |                  |
| 37–39   | 3 bytes | uint8 × 3   | Line Markers  | L1/L2 detection  |

### Field Notes

- **Voltage**: Input voltage from the power source.
- **Error Code** (byte 19): Present on v2/v3 devices only (0 = no
  error). On v1 devices this byte is unused and typically zero.
- **Bytes 20–30, 35–36**: Not parsed; contents undocumented.
- **Frequency**: AC line frequency.

## Dual-Line Detection (50A Models)

On 50A dual-line models (`PMD...`), L1 and L2 telemetry arrives as
alternating 40-byte frames — each frame carries data for one line only.
The **line markers** at bytes 37–39 determine which line the frame
belongs to.

The detection logic differs by hardware version:

### v2/v3 Devices (E3/E4)

- Markers `(1, 1, 1)` → **L2**
- Any other marker values → **L1**

### v1 Devices (E2)

- Markers `(0, 0, 0)` → **L2**, but only after dual-line capability
  has been confirmed
- Any non-zero marker → **L1**, and confirms the device is dual-line

On v1 devices, the first frame with non-zero markers confirms that the
device is a dual-line unit. Until that confirmation, `(0, 0, 0)` frames
are treated as L1 (since a single-line device would also produce zero
markers).

### Version Pre-seeding from BLE Name

Since the hardware version can be derived from the BLE advertised name
(`name[15:17]`), the line detection path can be pre-seeded before any
telemetry arrives. This eliminates a bootstrapping ambiguity where the
very first `(0, 0, 0)` frame on a v1 dual-line device would otherwise
be misassigned to L1.

## Error Codes

Gen1 devices support error codes 0–9 and 11–12. The error code is only
meaningful on v2/v3 hardware (byte 19); on v1 devices the byte is
typically zero regardless of device state.

| Code | Title                     |
|------|---------------------------|
| 0    | No Error                  |
| 1    | Line 1 Voltage Error      |
| 2    | Line 2 Voltage Error      |
| 3    | Line 1 Over Current       |
| 4    | Line 2 Over Current       |
| 5    | Line 1 Neutral Reversed   |
| 6    | Line 2 Neutral Reversed   |
| 7    | Missing Ground            |
| 8    | Neutral Missing           |
| 9    | Surge Protection Used Up  |
| 11   | Line 1 Frequency Error    |
| 12   | Line 2 Frequency Error    |

## Protocol Notes

- **No handshake**: Telemetry begins streaming as soon as the client
  subscribes to notifications on `0000ffe2`. No write is needed.
- **Fixed chunk size**: Every notification is exactly 20 bytes.
  Notifications of other sizes should be discarded.
- **Byte order**: All multi-byte telemetry values are big-endian
  **unsigned** 32-bit integers, unlike Gen2 which uses signed integers.
- **Polling rate**: The device streams telemetry continuously.
- **Reconnection**: If the BLE connection drops, re-subscribing to
  notifications on `0000ffe2` restarts the telemetry stream.
