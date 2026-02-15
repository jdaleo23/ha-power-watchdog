"""BLE connection manager and binary protocol parser for the Power Watchdog.

The device sends a framed binary protocol over GATT characteristic 0000ff01.
Each BLE notification carries a fragment of one or more packets.  A reassembly
buffer accumulates bytes until a complete packet can be extracted.

Packet layout
─────────────
    ┌─────────┬───┬───┬───┬────────┬──────────┬──────┐
    │ 24797740│ver│msg│cmd│dataLen │  body    │ 7121 │
    │  4 B    │1B │1B │1B │ 2 B BE │ N bytes  │ 2 B  │
    └─────────┴───┴───┴───┴────────┴──────────┴──────┘

DLReport (cmd 1) body contains one or two 34-byte *DLData* blocks:

    Offset  Len  Field             Scale
    ─────  ───  ────────────────  ───────
     0      4   inputVoltage      / 10 000  → V
     4      4   current           / 10 000  → A
     8      4   power             / 10 000  → W
    12      4   energy            / 10 000  → kWh
    16      4   (reserved)
    20      4   outputVoltage     / 10 000  → V
    24      1   backlight
    25      1   neutralDetection
    26      1   boost flag        1 = boosting
    27      1   temperature
    28      4   frequency         / 100     → Hz
    32      1   error code        0-9
    33      1   status

30A models send a single 34-byte block.
50A models send two consecutive blocks (L1 followed by L2, 68 bytes total).
"""

from __future__ import annotations

import asyncio
import logging
import struct
from dataclasses import dataclass, field

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.core import HomeAssistant, callback

from bleak import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

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

_LOGGER = logging.getLogger(__name__)


# ── Data model ──────────────────────────────────────────────────────────────


@dataclass
class LineData:
    """Parsed power data for a single AC line (L1 or L2)."""

    voltage: float | None = None
    current: float | None = None
    power: float | None = None
    energy: float | None = None
    output_voltage: float | None = None
    frequency: float | None = None
    error_code: int | None = None
    status: int | None = None
    boost: bool | None = None


@dataclass
class WatchdogData:
    """Container for the latest parsed telemetry."""

    l1: LineData = field(default_factory=LineData)
    l2: LineData = field(default_factory=LineData)
    has_l2: bool = False


# ── Manager ─────────────────────────────────────────────────────────────────


class PowerWatchdogManager:
    """Manages the Bluetooth connection and data parsing."""

    def __init__(self, hass: HomeAssistant, address: str, name: str) -> None:
        self.hass = hass
        self.address = address
        self.name = name
        self.client: BleakClientWithServiceCache | None = None
        self.sensors: list = []
        self.data = WatchdogData()

        # Packet reassembly buffer — BLE notifications may deliver partial
        # packets when the negotiated MTU is smaller than the full frame.
        self._rx_buffer = bytearray()

    def register_sensor(self, sensor) -> None:  # noqa: ANN001
        """Register a sensor entity for state updates."""
        self.sensors.append(sensor)

    # ── Connection lifecycle ────────────────────────────────────────────────

    async def connect_loop(self) -> None:
        """Maintain a persistent BLE connection with automatic retry."""
        while True:
            try:
                _LOGGER.debug("Connecting to Power Watchdog %s", self.address)

                device = async_ble_device_from_address(
                    self.hass, self.address, connectable=True
                )
                if not device:
                    _LOGGER.debug("Device not found. Waiting…")
                    await asyncio.sleep(10)
                    continue

                self.client = await establish_connection(
                    BleakClientWithServiceCache,
                    device,
                    name=self.name,
                    disconnected_callback=self._on_disconnected,
                )

                _LOGGER.debug("Connected. Subscribing to notifications…")
                self._rx_buffer.clear()
                await self.client.start_notify(
                    CHARACTERISTIC_UUID, self._notification_handler
                )

                _LOGGER.debug("Sending handshake…")
                await self.client.write_gatt_char(
                    CHARACTERISTIC_UUID, HANDSHAKE_PAYLOAD, response=True
                )

                # Keep alive while connected
                while self.client and self.client.is_connected:
                    await asyncio.sleep(5)

            except (BleakError, asyncio.TimeoutError) as ex:
                _LOGGER.warning("Connection failed: %s. Retrying in 10 s…", ex)
                await asyncio.sleep(10)
            except Exception as ex:  # noqa: BLE001
                _LOGGER.error("Unexpected error: %s", ex)
                await asyncio.sleep(30)

    def _on_disconnected(self, _client) -> None:  # noqa: ANN001
        _LOGGER.debug("Disconnected from Power Watchdog")

    # ── Notification handling / packet reassembly ───────────────────────────

    @callback
    def _notification_handler(self, _sender, raw: bytearray) -> None:  # noqa: ANN001
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

    def _try_parse_packet(self) -> bool:
        """Extract and dispatch one packet from the buffer.

        Returns True if bytes were consumed (even on an invalid packet),
        False when more data is needed.
        """
        buf = self._rx_buffer

        # Scan for the 4-byte identifier
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
            return False  # incomplete — wait for more data

        body = bytes(buf[HEADER_SIZE : HEADER_SIZE + data_len])
        tail = struct.unpack_from(">H", buf, HEADER_SIZE + data_len)[0]

        del buf[:total_len]

        if tail != PACKET_TAIL:
            _LOGGER.debug(
                "Bad tail 0x%04X (expected 0x%04X), discarding packet", tail, PACKET_TAIL
            )
            return True

        # Dispatch
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
        if len(body) == DL_DATA_SIZE:
            self.data.l1 = self._parse_dl_data(body, 0)
            self.data.has_l2 = False
        elif len(body) == DL_DATA_SIZE * 2:
            self.data.l1 = self._parse_dl_data(body, 0)
            self.data.l2 = self._parse_dl_data(body, DL_DATA_SIZE)
            self.data.has_l2 = True
        else:
            _LOGGER.warning(
                "Unexpected DLReport body length %d (expected %d or %d)",
                len(body),
                DL_DATA_SIZE,
                DL_DATA_SIZE * 2,
            )
            return

        # Push update to all registered sensor entities
        for sensor in self.sensors:
            sensor.async_write_ha_state()

    @staticmethod
    def _parse_dl_data(body: bytes, offset: int) -> LineData:
        """Parse a single 34-byte DLData block."""
        o = offset
        voltage_raw = struct.unpack_from(">i", body, o)[0]
        current_raw = struct.unpack_from(">i", body, o + 4)[0]
        power_raw = struct.unpack_from(">i", body, o + 8)[0]
        energy_raw = struct.unpack_from(">i", body, o + 12)[0]
        # o+16 … o+19 = reserved (temp1)
        output_v_raw = struct.unpack_from(">i", body, o + 20)[0]
        boost = body[o + 26] == 1
        freq_raw = struct.unpack_from(">i", body, o + 28)[0]
        error_code = body[o + 32]
        status = body[o + 33]

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
