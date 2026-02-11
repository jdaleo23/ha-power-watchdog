import logging
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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_DEVICE_NAME
from .models import PowerWatchdogManager 

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager = hass.data[DOMAIN][entry.entry_id]["manager"]
    
    sensors = [
        PowerWatchdogSensor(manager, "Voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, "volts"),
        PowerWatchdogSensor(manager, "Current", SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE, "amps"),
        PowerWatchdogSensor(manager, "Power", SensorDeviceClass.POWER, UnitOfPower.WATT, "watts"),
        PowerWatchdogSensor(manager, "Total Energy", SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, "energy"),
        PowerWatchdogSensor(manager, "Frequency", SensorDeviceClass.FREQUENCY, UnitOfFrequency.HERTZ, "freq"),
    ]

    async_add_entities(sensors)

class PowerWatchdogSensor(SensorEntity):
    """Representation of a Power Watchdog Sensor."""

    _attr_should_poll = False

    def __init__(self, manager, name_suffix, device_class, unit, data_key):
        """Initialize the sensor."""
        self._manager = manager
        self._key = data_key
        self._attr_name = f"{manager.name} {name_suffix}"
        self._attr_unique_id = f"{manager.address}_{data_key}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit

        if device_class == SensorDeviceClass.ENERGY:
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        else:
            self._attr_state_class = SensorStateClass.MEASUREMENT

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, manager.address)},
            name=manager.name,
            manufacturer="Hughes Autoformers",
            model="Power Watchdog Gen 2",
        )
        manager.register_sensor(self)

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._manager.data.get(self._key)
