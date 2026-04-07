# Gen2 Power Watchdog BLE Protocol

Gen2 (WiFi+BT) Power Watchdog devices use a custom framed binary
protocol over a single BLE characteristic. They advertise a BLE name
in the format `WD_{type}_{serial}`, where `{type}` is a two-character
model code and `{serial}` is a 12-character lowercase hex string.

## Device Models

| Type | Amperage | Lines  | Voltage Booster |
|------|----------|--------|-----------------|
| E5   | 30A      | Single | No              |
| V5   | 30A      | Single | No              |
| E6   | 30A      | Single | No              |
| V6   | 30A      | Single | No              |
| E7   | 50A      | Dual   | No              |
| V7   | 50A      | Dual   | No              |
| E8   | 50A      | Dual   | Yes             |
| V8   | 50A      | Dual   | Yes             |
| E9   | 50A      | Dual   | Yes             |
| V9   | 50A      | Dual   | Yes             |

The second character of the type code determines capabilities:
- `5` or `6` = 30A single-line surge protector
- `7` = 50A dual-line surge protector
- `8` or `9` = 50A dual-line with voltage booster (Hughes Autoformer)

## GATT Service

All communication occurs over a single GATT characteristic:

| Property        | Value                                  |
|-----------------|----------------------------------------|
| Characteristic  | `0000ff01-0000-1000-8000-00805f9b34fb` |
| Properties      | Notify, Write                          |
| Direction       | Notify = device-to-host, Write = host-to-device |

The same UUID is used for both subscribing to notifications (data from
the device) and writing commands (to the device).

## Connection Sequence

1. Scan for BLE devices with names matching `WD_*`
2. Connect to the device
3. Subscribe to notifications on characteristic `0000ff01`
4. Request MTU 230 (the device sends large packets)
5. Send the handshake payload (see below)
6. Begin receiving framed data packets via notifications

### Handshake

The handshake is an ASCII string written to the characteristic:

```
!%!%,protocol,open,
```

Hex: `21 25 21 25 2c 70 72 6f 74 6f 63 6f 6c 2c 6f 70 65 6e 2c`

The write must use `response=True` (write-with-response). After the
handshake, the device begins streaming DLReport packets via
notifications.

## Packet Framing

BLE notifications may contain partial packets. Data must be buffered
and reassembled. Each complete packet has the following structure:

| Offset | Size    | Field          | Description                      |
|--------|---------|----------------|----------------------------------|
| 0      | 4 bytes | Identifier     | Magic: `0x24797740`              |
| 4      | 1 byte  | Version        | Protocol version                 |
| 5      | 1 byte  | Message ID     | Sequence number                  |
| 6      | 1 byte  | Command        | Packet type (see below)          |
| 7      | 2 bytes | Data Length     | Big-endian, length of body       |
| 9      | N bytes | Body           | Command-specific payload         |
| 9+N    | 2 bytes | Tail           | Magic: `0x7121`                  |

Total packet size: 9 (header) + N (body) + 2 (tail) = N + 11 bytes.

### Command Types

| Command | Name          | Description                                |
|---------|---------------|--------------------------------------------|
| 1       | DLReport      | Live power data (primary data stream)      |
| 2       | ErrorReport   | Error condition notification               |
| 14      | Alarm         | Alarm notification                         |

## DLReport (Command 1)

The DLReport body contains one or two 34-byte DLData blocks:

- **30A (single-line)**: 34 bytes total (one DLData block for L1)
- **50A (dual-line)**: 68 bytes total (two DLData blocks, L1 then L2)

### DLData Block (34 bytes)

Each 34-byte block represents measurements for a single AC line.
All multi-byte integers are **big-endian signed 32-bit** (`int32`).

| Offset | Size    | Type         | Field             | Unit / Scale          |
|--------|---------|--------------|-------------------|-----------------------|
| 0      | 4 bytes | int32 (BE)   | Input Voltage     | /10000 = Volts        |
| 4      | 4 bytes | int32 (BE)   | Current           | /10000 = Amps         |
| 8      | 4 bytes | int32 (BE)   | Power             | /10000 = Watts        |
| 12     | 4 bytes | int32 (BE)   | Energy            | /10000 = kWh (cumulative) |
| 16     | 4 bytes | int32 (BE)   | Temperature 1     | Reserved (unused)     |
| 20     | 4 bytes | int32 (BE)   | Output Voltage    | /10000 = Volts        |
| 24     | 1 byte  | uint8        | Backlight         |                       |
| 25     | 1 byte  | uint8        | Neutral Detection |                       |
| 26     | 1 byte  | uint8        | Boost Flag        | 1 = boosting          |
| 27     | 1 byte  | uint8        | Temperature       | Degrees; E8/V8 only   |
| 28     | 4 bytes | int32 (BE)   | Frequency         | /100 = Hz             |
| 32     | 1 byte  | uint8        | Error Code        | 0-14 (see table below)|
| 33     | 1 byte  | uint8        | Status            |                       |

### Field Notes

- **Input Voltage**: Voltage at the power source (pedestal/shore power).
- **Output Voltage**: Voltage after the Watchdog's regulation/protection.
  May differ from input voltage when the boost feature is active.
  **Booster models only** (E8/V8, E9/V9) — see
  [Model-Specific Fields](#model-specific-fields) below.
- **Energy**: Cumulative kilowatt-hours since the device was last reset.
- **Boost Flag**: Set to `1` when the device is actively boosting low
  voltage. **Booster models only** (E8/V8, E9/V9).
- **Neutral Detection**: Indicates the state of neutral wire detection.
- **Backlight**: Display backlight state on the physical device.
- **Temperature 1** (offset 16): Reserved; not used in current firmware.
- **Temperature** (offset 27): Device internal temperature reading.
  **Booster models only** (E8/V8, E9/V9) — non-booster models
  transmit `0` for this byte.
- **Status**: Device operational status byte.

### Model-Specific Fields

Not all Gen2 models support every field in the DLData block. The type
code's second character determines the model family:

- **E5/V5, E6/V6, E7/V7** ("Non-booster" / surge protector only):
  - **Output Voltage** (offset 20): Not meaningful. The firmware
    repurposes these bytes with the cumulative energy counter value,
    causing the field to mirror the Energy field. Implementations
    should suppress or ignore this field on non-booster models.
  - **Boost Flag** (offset 26): Always `0`. Not applicable.
  - **Temperature** (offset 27): Always `0`. Not applicable.

- **E8/V8, E9/V9** ("Booster" / Hughes Autoformer models):
  - **Output Voltage** (offset 20): Reports the actual output voltage
    after boost regulation. May differ from input voltage when the
    booster is active.
  - **Boost Flag** (offset 26): `1` when the booster is actively
    raising voltage, `0` otherwise.
  - **Temperature** (offset 27): Device internal temperature in
    degrees Celsius. Used for over-temperature protection (alarm
    triggers at 74°C).

Implementers should detect the model from the BLE name type code and
suppress the Output Voltage, Boost, and Temperature fields for
non-booster models (type digits `5`, `6`, `7`).

## Error Codes

The error code field (byte 32 of each DLData block) reports the current
fault condition for that AC line.

| Code | Title                     | Description |
|------|---------------------------|-------------|
| 0    | No Error                  | Normal operation. |
| 1    | Line 1 Voltage Error      | Input voltage has exceeded 132V or dropped below 104V. The Watchdog has shut off power to protect the RV. Power will be restored automatically after voltage remains in the safe range for 90 seconds. |
| 2    | Line 2 Voltage Error      | Same as code 1, but on Line 2 (50A models only). |
| 3    | Line 1 Over Current       | Current draw exceeds the rated amperage on Line 1. |
| 4    | Line 2 Over Current       | Same as code 3, but on Line 2 (50A models only). |
| 5    | Line 1 Neutral Reversed   | Hot and neutral wires are reversed at the power source. |
| 6    | Line 2 Neutral Reversed   | Same as code 5, but on Line 2 (50A models only). |
| 7    | Missing Ground            | The ground connection has been lost. |
| 8    | Neutral Missing           | The neutral return path is absent inside the RV. |
| 9    | Surge Protection Used Up  | The surge absorption capacity has been exhausted. The RV continues to operate but is no longer surge-protected. |
| 10   | (Reserved)                | Not used. |
| 11   | Line 1 Frequency Error    | AC frequency on Line 1 is outside the acceptable range. |
| 12   | Line 2 Frequency Error    | AC frequency on Line 2 is outside the acceptable range. |
| 13   | Over Temperature          | Device internal temperature has exceeded the safe threshold (74°C). Booster models only (E8/V8, E9/V9). |
| 14   | Boost Error               | Voltage booster malfunction. Reported on booster models (E8/V8, E9/V9) and select surge protector models (E5/V5, E6/V6). |

## ErrorReport (Command 2)

An ErrorReport packet is sent by the device when an error condition
changes. The body format is not fully documented but accompanies the
error code already present in the DLReport data.

## Alarm (Command 14)

An Alarm packet indicates an urgent condition reported by the device.
The body format is not fully documented.

## Protocol Notes

- **MTU**: The device benefits from an MTU of 230 bytes. Smaller MTUs
  will cause DLReport packets (up to 79 bytes framed) to be fragmented
  across multiple BLE notifications, requiring reassembly.
- **Fragmentation**: Notifications may contain partial packets.
  Implementers must buffer incoming data and scan for the 4-byte
  identifier (`0x24797740`) to find packet boundaries.
- **Byte order**: All multi-byte fields in the packet header and DLData
  blocks are big-endian.
- **Polling rate**: The device streams DLReport packets continuously
  after the handshake. Typical intervals are 100-500ms.
- **Reconnection**: If the BLE connection drops, the full connection
  sequence (subscribe, handshake) must be repeated.
