import asyncio
import logging
import struct

from bleak import BleakError
from homeassistant.components.bluetooth import (
    async_bleak_client_create,
    async_register_callback,
    BluetoothChange,
    BluetoothServiceInfoBleak,
)
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ADDRESS,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfPower,
    UnitOfEnergy,
    UnitOfFrequency,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SERVICE_UUID, HANDSHAKE_PAYLOAD, CONF_DEVICE_NAME

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Power Watchdog sensors."""
    address = entry.data[CONF_ADDRESS]
    name = entry.data[CONF_DEVICE_NAME]

    # Create the data manager
    manager = PowerWatchdogManager(hass, address, name)
    
    # Create entities
    sensors = [
        PowerWatchdogSensor(manager, "Voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, "volts"),
        PowerWatchdogSensor(manager, "Current", SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE, "amps"),
        PowerWatchdogSensor(manager, "Power", SensorDeviceClass.POWER, UnitOfPower.WATT, "watts"),
        PowerWatchdogSensor(manager, "Energy", SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, "energy"),
        PowerWatchdogSensor(manager, "Frequency", SensorDeviceClass.FREQUENCY, UnitOfFrequency.HERTZ, "freq"),
    ]

    async_add_entities(sensors)
    # Start the connection loop in the background
    entry.async_create_background_task(hass, manager.connect_loop(), "power_watchdog_loop")


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
                # Use HA's helper to create a client that works with proxies
                self.client = await async_bleak_client_create(
                    self.hass, self.address, disconnected_callback=self._on_disconnected
                )

                if not self.client.is_connected:
                    await self.client.connect()

                _LOGGER.debug("Connected. Subscribing...")
                await self.client.start_notify(SERVICE_UUID, self._notification_handler)

                _LOGGER.debug("Sending Handshake...")
                await self.client.write_gatt_char(SERVICE_UUID, HANDSHAKE_PAYLOAD, response=True)
                
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
        """Parse the raw bytes (Logic from our Python script)."""
        if len(data) <= 30:
            return

        try:
            # Unpack Big Endian
            volts_raw, amps_raw, watts_raw, energy_raw = struct.unpack('>IIII', data[9:25])
            freq_raw = struct.unpack('>I', data[37:41])[0]

            self.data["volts"] = volts_raw / 10000.0
            self.data["amps"] = amps_raw / 10000.0
            self.data["watts"] = watts_raw / 10000.0
            self.data["energy"] = energy_raw / 10000.0
            self.data["freq"] = freq_raw / 100.0

            # Update all sensors
            for sensor in self.sensors:
                sensor.async_write_ha_state()

        except Exception as e:
            _LOGGER.debug("Parse error: %s", e)


class PowerWatchdogSensor(SensorEntity):
    """Representation of a Power Watchdog Sensor."""

    _attr_should_poll = False
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, manager, name_suffix, device_class, unit, data_key):
        self._manager = manager
        self._key = data_key
        self._attr_name = f"{manager.name} {name_suffix}"
        self._attr_unique_id = f"{manager.address}_{data_key}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, manager.address)},
            name=manager.name,
            manufacturer="Hughes Autoformers",
            model="Power Watchdog V2",
        )
        manager.register_sensor(self)

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._manager.data.get(self._key)