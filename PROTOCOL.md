# Hughes Power Watchdog BLE Protocol

Hughes shipped two generations of Power Watchdog surge protectors with
**completely different** BLE protocols. Despite sharing the Power
Watchdog brand, the two generations have different GATT characteristics,
different data framing, different byte signedness, and different
connection sequences.

Each generation has its own protocol document:

- **[Gen2 Protocol](PROTOCOL-GEN2.md)** — WiFi+BT devices (`WD_*` names).
  Custom framed binary protocol on characteristic `0000ff01`. Requires
  an ASCII handshake to start data flow. Uses signed int32 values in
  34-byte DLData blocks.

- **[Gen1 Protocol](PROTOCOL-GEN1.md)** — BT-only devices (`PM*` names).
  Raw Modbus-style 20-byte notification pairs on Nordic UART
  characteristics (`0000ffe2` / `0000fff5`). No handshake — telemetry
  starts immediately on subscribe. Uses unsigned uint32 values in
  40-byte merged buffers.

## Key Differences

| Aspect                 | Gen1 (BT-only)                   | Gen2 (WiFi+BT)                    |
|------------------------|----------------------------------|------------------------------------|
| BLE name pattern       | `PM{S\|D}...` (19 chars)        | `WD_{type}_{serial}`               |
| GATT notify            | `0000ffe2`                       | `0000ff01`                         |
| GATT write             | `0000fff5`                       | `0000ff01` (same as notify)        |
| Handshake              | None                             | `!%!%,protocol,open,`              |
| Framing                | Raw 20+20 byte chunk pairs       | Magic header/tail framed packets   |
| Telemetry size         | 40 bytes (merged)                | 34 bytes per line (DLData block)   |
| Integer signedness     | Unsigned (`uint32`)              | Signed (`int32`)                   |
| Dual-line delivery     | Alternating frames, one line each| Single packet with both lines      |
| Hardware versions      | v1 (E2), v2 (E3), v3 (E4)       | Single version                     |
| Error code byte        | Byte 19 (v2/v3 only)            | Byte 32 of DLData                  |
| Error code range       | 0–9, 11–12                       | 0–9, 11–14                         |

## Error Behaviour

Both generations share the same error semantics:

- When an error is detected, the Watchdog disconnects park power from
  the RV to prevent damage.
- For most error conditions (1, 2, 5, 7, 8), the Watchdog continuously
  monitors and automatically restores power after the fault clears and
  a 90-second safety delay passes.
- Error 9 (surge protection used up) is a warning only; power is not
  disconnected, but the RV is no longer surge-protected.
- Error codes are reported per-line. On 50A dual-line models, each line
  has its own independent error code. A dual-line device may report
  different error codes on L1 and L2 simultaneously.
