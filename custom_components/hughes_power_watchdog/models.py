"""BLE connection manager and data model for the Power Watchdog.

The manager maintains a persistent BLE connection and delegates protocol
handling to a generation-specific handler:

- Gen2 (WD_* devices): Framed binary protocol on characteristic 0000ff01
  with an ASCII handshake.  See ``protocol_gen2.py``.
- Gen1 (PM* devices):  Raw Modbus-style 20-byte chunks on Nordic UART
  characteristics (ffe2/fff5), no handshake.  See ``protocol_gen1.py``.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.core import HomeAssistant

from bleak import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .const import GEN1_PREFIX

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

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        name: str,
        ble_name: str = "",
    ) -> None:
        self.hass = hass
        self.address = address
        self.name = name
        self.ble_name = ble_name
        self.client: BleakClientWithServiceCache | None = None
        self.sensors: list = []
        self.data = WatchdogData()

        self._protocol = self._init_protocol()

    @property
    def generation(self) -> int:
        """Device generation (1 or 2)."""
        return self._protocol.generation

    def _init_protocol(self):  # noqa: ANN202
        """Create the appropriate protocol handler based on BLE name."""
        if self.ble_name.startswith(GEN1_PREFIX):
            from .protocol_gen1 import Gen1Protocol
            return Gen1Protocol(self, self.ble_name)
        from .protocol_gen2 import Gen2Protocol
        return Gen2Protocol(self)

    def register_sensor(self, sensor) -> None:  # noqa: ANN001
        """Register a sensor entity for state updates."""
        self.sensors.append(sensor)

    def notify_sensors(self) -> None:
        """Push updated data to all registered sensor entities."""
        for sensor in self.sensors:
            if sensor.hass:
                sensor.async_write_ha_state()

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
                self._protocol.reset_state()
                await self.client.start_notify(
                    self._protocol.notify_uuid,
                    self._protocol.notification_handler,
                )

                await self._protocol.after_subscribe(self.client)

                while self.client and self.client.is_connected:
                    await asyncio.sleep(5)

            except asyncio.CancelledError:
                _LOGGER.debug("Task cancelled, disconnecting...")
                try:
                    if self.client:
                        await self.client.disconnect()
                except Exception as ex:
                    _LOGGER.debug("Error during disconnect cleanup: %s", ex)
                finally:
                    raise

            except (BleakError, asyncio.TimeoutError) as ex:
                _LOGGER.warning("Connection failed: %s. Retrying in 10 s…", ex)
                await asyncio.sleep(10)
            except Exception as ex:  # noqa: BLE001
                _LOGGER.error("Unexpected error: %s", ex)
                await asyncio.sleep(30)

    def _on_disconnected(self, _client) -> None:  # noqa: ANN001
        _LOGGER.debug("Disconnected from Power Watchdog")
