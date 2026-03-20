"""Gen2 Power Watchdog framed binary protocol (WiFi+BT, WD_* devices).

Gen2 devices use a custom framed protocol over GATT characteristic 0000ff01.
After subscribing to notifications, an ASCII handshake starts the data flow.
Incoming bytes are buffered and reassembled into packets delimited by a
4-byte magic header (0x24797740) and 2-byte tail (0x7121).

DLReport (cmd 1) body contains one or two 34-byte DLData blocks using
big-endian **signed** int32 values.
"""

from __future__ import annotations

import logging
import struct
from typing import TYPE_CHECKING

from homeassistant.core import callback

from .const import (
    CHARACTERISTIC_UUID,
    CMD_ALARM,
    CMD_DL_REPORT,
    CMD_ERROR_REPORT,
    DL_DATA_SIZE,
    HANDSHAKE_PAYLOAD,
    HEADER_SIZE,
    MAX_BUFFER_SIZE,
    PACKET_IDENTIFIER,
    PACKET_TAIL,
    TAIL_SIZE,
)

if TYPE_CHECKING:
    from bleak import BleakClient
    from .models import PowerWatchdogManager

_LOGGER = logging.getLogger(__name__)


class Gen2Protocol:
    """Gen2 framed binary protocol handler."""

    notify_uuid = CHARACTERISTIC_UUID
    generation = 2

    def __init__(self, manager: PowerWatchdogManager) -> None:
        self._manager = manager
        self._rx_buffer = bytearray()

    def reset_state(self) -> None:
        """Clear protocol state for a new connection."""
        self._rx_buffer.clear()

    @callback
    def notification_handler(self, _sender, raw: bytearray) -> None:  # noqa: ANN001
        """Accumulate raw BLE bytes and extract complete packets."""
        self._rx_buffer.extend(raw)

        if len(self._rx_buffer) > MAX_BUFFER_SIZE:
            _LOGGER.warning(
                "RX buffer overflow (%d bytes), clearing", len(self._rx_buffer)
            )
            self._rx_buffer.clear()
            return

        while self._try_parse_packet():
            pass

    async def after_subscribe(self, client: BleakClient) -> None:
        """Send the ASCII handshake to start data flow."""
        _LOGGER.debug("Sending Gen2 handshake…")
        await client.write_gatt_char(
            CHARACTERISTIC_UUID, HANDSHAKE_PAYLOAD, response=True
        )

    # ── Packet parsing ──────────────────────────────────────────────────────

    def _try_parse_packet(self) -> bool:
        """Extract and dispatch one packet from the buffer."""
        buf = self._rx_buffer

        while len(buf) >= 4:
            if struct.unpack_from(">I", buf, 0)[0] == PACKET_IDENTIFIER:
                break
            del buf[0]

        if len(buf) < HEADER_SIZE:
            return False

        cmd = buf[6]
        data_len = struct.unpack_from(">H", buf, 7)[0]

        if data_len > MAX_BUFFER_SIZE:
            _LOGGER.debug("Invalid dataLen %d, skipping identifier", data_len)
            del buf[:4]
            return True

        total_len = HEADER_SIZE + data_len + TAIL_SIZE
        if len(buf) < total_len:
            return False

        body = bytes(buf[HEADER_SIZE : HEADER_SIZE + data_len])
        tail = struct.unpack_from(">H", buf, HEADER_SIZE + data_len)[0]

        del buf[:total_len]

        if tail != PACKET_TAIL:
            _LOGGER.debug(
                "Bad tail 0x%04X (expected 0x%04X), discarding packet",
                tail, PACKET_TAIL,
            )
            return True

        if cmd == CMD_DL_REPORT:
            self._parse_dl_report(body)
        elif cmd == CMD_ERROR_REPORT:
            _LOGGER.debug("ErrorReport received (%d bytes)", len(body))
        elif cmd == CMD_ALARM:
            _LOGGER.warning("Alarm notification from Power Watchdog")
        else:
            _LOGGER.debug("Unknown cmd %d (%d bytes)", cmd, len(body))

        return True

    # ── DLReport parsing ────────────────────────────────────────────────────

    def _parse_dl_report(self, body: bytes) -> None:
        """Parse a DLReport body into L1 (and optionally L2) data."""
        data = self._manager.data

        if len(body) == DL_DATA_SIZE:
            data.l1 = parse_dl_data(body, 0)
            data.has_l2 = False
        elif len(body) == DL_DATA_SIZE * 2:
            data.l1 = parse_dl_data(body, 0)
            data.l2 = parse_dl_data(body, DL_DATA_SIZE)
            data.has_l2 = True
        else:
            _LOGGER.warning(
                "Unexpected DLReport body length %d (expected %d or %d)",
                len(body), DL_DATA_SIZE, DL_DATA_SIZE * 2,
            )
            return

        self._manager.notify_sensors()


def parse_dl_data(body: bytes, offset: int):
    """Parse a single 34-byte DLData block (big-endian signed int32)."""
    from .models import LineData

    o = offset
    voltage_raw  = struct.unpack_from(">i", body, o)[0]
    current_raw  = struct.unpack_from(">i", body, o + 4)[0]
    power_raw    = struct.unpack_from(">i", body, o + 8)[0]
    energy_raw   = struct.unpack_from(">i", body, o + 12)[0]
    output_v_raw = struct.unpack_from(">i", body, o + 20)[0]
    boost        = body[o + 26] == 1
    freq_raw     = struct.unpack_from(">i", body, o + 28)[0]
    error_code   = body[o + 32]
    status       = body[o + 33]

    return LineData(
        voltage=round(voltage_raw / 10_000, 1),
        current=round(current_raw / 10_000, 2),
        power=round(power_raw / 10_000, 1),
        energy=round(energy_raw / 10_000, 2),
        output_voltage=round(output_v_raw / 10_000, 1),
        frequency=round(freq_raw / 100, 1),
        error_code=error_code,
        status=status,
        boost=boost,
    )
