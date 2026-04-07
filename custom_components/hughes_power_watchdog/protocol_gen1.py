"""Gen1 Power Watchdog raw Modbus-style BLE protocol (BT-only, PM* devices).

Gen1 devices stream telemetry without any handshake over Nordic UART-style
characteristics (TX: 0000ffe2, RX: 0000fff5).  Data arrives as pairs of
20-byte BLE notifications:

1. First chunk starts with ``01 03 20`` (Modbus read-holding-registers
   response: slave 1, function 3, 32 data bytes).
2. Second chunk is appended to form a 40-byte merged buffer.

All multi-byte telemetry values are big-endian **unsigned** int32, unlike
Gen2 which uses signed int32.

For 50A dual-line models, L1 and L2 updates alternate as separate 40-byte
frames.  Line detection uses bytes [37:40] and differs by hardware version:
    - v2/v3 (E3/E4): markers (1,1,1) = L2, anything else = L1
    - v1    (E2):     markers (0,0,0) = L2 after dual-line confirmed,
                      non-zero markers = L1 and confirms dual-line
"""

from __future__ import annotations

import logging
import struct
from typing import TYPE_CHECKING

from homeassistant.core import callback

from .const import (
    GEN1_CHUNK_SIZE,
    GEN1_DUAL_PREFIX,
    GEN1_HEADER,
    GEN1_HW_VERSIONS,
    GEN1_MERGED_SIZE,
    GEN1_TX_UUID,
)

if TYPE_CHECKING:
    from bleak import BleakClient
    from .models import PowerWatchdogManager

_LOGGER = logging.getLogger(__name__)


class Gen1Protocol:
    """Gen1 raw Modbus-style telemetry protocol handler."""

    notify_uuid = GEN1_TX_UUID
    generation = 1

    def __init__(self, manager: PowerWatchdogManager, ble_name: str) -> None:
        self._manager = manager
        self._first_chunk: bytes | None = None
        self._is_v2v3 = False

        self._init_from_name(ble_name)

    def _init_from_name(self, ble_name: str) -> None:
        """Pre-seed hardware version and line type from the BLE name.

        Gen1 names are 19 characters: ``PM{S|D}...{E2|E3|E4}...``
        Position 2 encodes line type (S=single, D=dual).
        Positions 15-16 encode hardware version code.
        """
        stripped = ble_name.rstrip()
        if len(stripped) < 17:
            return

        hw_code = stripped[15:17]
        hw_ver = GEN1_HW_VERSIONS.get(hw_code)
        if hw_ver is None:
            return

        if hw_ver in (2, 3):
            self._is_v2v3 = True
            _LOGGER.debug(
                "Gen1 v%d detected from BLE name — using (1,1,1) L2 markers",
                hw_ver,
            )

        if hw_ver == 1 and ble_name.startswith(GEN1_DUAL_PREFIX):
            self._manager.data.has_l2 = True
            _LOGGER.debug("Gen1 v1 dual-line detected from BLE name")

    def reset_state(self) -> None:
        """Clear protocol state for a new connection."""
        self._first_chunk = None

    @callback
    def notification_handler(self, _sender, data: bytearray) -> None:  # noqa: ANN001
        """Reassemble 20-byte chunk pairs into 40-byte telemetry frames."""
        if len(data) != GEN1_CHUNK_SIZE:
            _LOGGER.debug(
                "Gen1: ignoring %d-byte notification (expected %d)",
                len(data), GEN1_CHUNK_SIZE,
            )
            return

        if data[:3] == GEN1_HEADER:
            self._first_chunk = bytes(data)
            return

        first = self._first_chunk
        if first is None or len(first) != GEN1_CHUNK_SIZE:
            return

        self._first_chunk = None
        merged = first + bytes(data)
        self._parse_telemetry(merged)

    async def after_subscribe(self, client: BleakClient) -> None:
        """No-op — Gen1 streams telemetry without a handshake."""
        _LOGGER.debug(
            "Gen1 UART mode: waiting for raw telemetry "
            "(20+20 byte chunks, header 01 03 20)…",
        )

    # ── Telemetry parsing ───────────────────────────────────────────────────

    def _parse_telemetry(self, buf: bytes) -> None:
        """Parse a 40-byte merged Gen1 telemetry buffer."""
        from .models import LineData

        if len(buf) != GEN1_MERGED_SIZE:
            _LOGGER.warning(
                "Gen1 merged buffer wrong size: %d (expected %d)",
                len(buf), GEN1_MERGED_SIZE,
            )
            return

        voltage   = struct.unpack_from(">I", buf, 3)[0] / 10_000
        current   = struct.unpack_from(">I", buf, 7)[0] / 10_000
        power     = struct.unpack_from(">I", buf, 11)[0] / 10_000
        energy    = struct.unpack_from(">I", buf, 15)[0] / 10_000
        error_code = buf[19]
        frequency = struct.unpack_from(">I", buf, 31)[0] / 100

        markers = (buf[37], buf[38], buf[39])

        ld = LineData(
            voltage=round(voltage, 1),
            current=round(current, 2),
            power=round(power, 1),
            energy=round(energy, 2),
            frequency=round(frequency, 1),
            error_code=error_code,
        )

        data = self._manager.data

        if markers == (1, 1, 1):
            self._is_v2v3 = True
            data.l2 = ld
            data.has_l2 = True
        elif self._is_v2v3:
            data.l1 = ld
        elif markers == (0, 0, 0):
            if data.has_l2:
                data.l2 = ld
            else:
                data.l1 = ld
        else:
            data.l1 = ld
            data.has_l2 = True

        self._manager.notify_sensors()
