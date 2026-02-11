import asyncio
import logging
import struct

from homeassistant.components.bluetooth import (
    async_bleak_client_create,
)
from homeassistant.core import HomeAssistant, callback
from bleak import BleakError

from .const import CHARACTERISTIC_UUID, HANDSHAKE_PAYLOAD

_LOGGER = logging.getLogger(__name__)

class PowerWatchdogManager:
    """Manages the Bluetooth connection and data parsing."""

    def __init__(self, hass: HomeAssistant, address: str, name: str):
        self.hass = hass
        self.address = address
        self.name = name
        self.client = None
        self.sensors = []
        self.data = {}

    def register_sensor(self, sensor):
        self.sensors.append(sensor)

    async def connect_loop(self):
        """Main loop to maintain connection."""
        while True:
            try:
                _LOGGER.debug("Connecting to Power Watchdog %s", self.address)
                self.client = await async_bleak_client_create(
                    self.hass, self.address, disconnected_callback=self._on_disconnected
                )

                if not self.client.is_connected:
                    await self.client.connect()

                _LOGGER.debug("Connected. Subscribing...")
                await self.client.start_notify(CHARACTERISTIC_UUID, self._notification_handler)

                _LOGGER.debug("Sending Handshake...")
                await self.client.write_gatt_char(CHARACTERISTIC_UUID, HANDSHAKE_PAYLOAD, response=True)
                
                # Keep connection alive
                while self.client and self.client.is_connected:
                    await asyncio.sleep(5)

            except (BleakError, asyncio.TimeoutError) as ex:
                _LOGGER.warning("Connection failed: %s. Retrying in 10s...", ex)
                await asyncio.sleep(10)
            except Exception as ex:
                _LOGGER.error("Unexpected error: %s", ex)
                await asyncio.sleep(30)

    def _on_disconnected(self, client):
        _LOGGER.debug("Disconnected from Power Watchdog")

    @callback
    def _notification_handler(self, sender, data):
        """Corrected V2 Parse Logic."""
        if len(data) < 30:
            return

        try:
            volts_raw = struct.unpack('>I', data[9:13])[0]
            amps_raw = struct.unpack('>I', data[13:17])[0]
            watts_raw = struct.unpack('>I', data[17:21])[0]  # Watts
            energy_raw = struct.unpack('>I', data[21:25])[0] # kWh

            self.data["volts"] = volts_raw / 10000.0
            self.data["amps"] = amps_raw / 10000.0
            self.data["watts"] = watts_raw / 10000.0
            self.data["energy"] = energy_raw / 10000.0
            
            if len(data) >= 41:
                freq_raw = struct.unpack('>I', data[37:41])[0]
                self.data["freq"] = freq_raw / 100.0

            for sensor in self.sensors:
                sensor.async_write_ha_state()

        except Exception as e:
            _LOGGER.debug("Parse error: %s", e)
