"""Sensor platform for the Hughes Power Watchdog integration.

Creates sensor entities for L1, L2 (50A models), and combined totals.
L2 sensors will report *unavailable* on 30A single-line models.
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE_NAME, DOMAIN, ERROR_CODES
from .models import PowerWatchdogManager

_LOGGER = logging.getLogger(__name__)


def _device_info(manager: PowerWatchdogManager) -> DeviceInfo:
    """Build the shared DeviceInfo dict for all sensor entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, manager.address)},
        name=manager.name,
        manufacturer="Hughes Autoformers",
        model="Power Watchdog",
    )


def _error_attributes(code: int | None) -> dict[str, str | None]:
    """Return human-readable error title and description for a given code."""
    if code is not None and code in ERROR_CODES:
        title, description = ERROR_CODES[code]
    else:
        title = None
        description = None
    return {"error_title": title, "error_description": description}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Power Watchdog sensor entities."""
    manager: PowerWatchdogManager = hass.data[DOMAIN][entry.entry_id]["manager"]

    sensors: list[SensorEntity] = [
        # ── L1 ──────────────────────────────────────────────────────────────
        PowerWatchdogLineSensor(manager, "L1 Voltage", SensorDeviceClass.VOLTAGE,
                               UnitOfElectricPotential.VOLT, "l1", "voltage"),
        PowerWatchdogLineSensor(manager, "L1 Current", SensorDeviceClass.CURRENT,
                               UnitOfElectricCurrent.AMPERE, "l1", "current"),
        PowerWatchdogLineSensor(manager, "L1 Power", SensorDeviceClass.POWER,
                               UnitOfPower.WATT, "l1", "power"),
        PowerWatchdogLineSensor(manager, "L1 Energy", SensorDeviceClass.ENERGY,
                               UnitOfEnergy.KILO_WATT_HOUR, "l1", "energy",
                               state_class=SensorStateClass.TOTAL_INCREASING),
        PowerWatchdogLineSensor(manager, "L1 Frequency", SensorDeviceClass.FREQUENCY,
                               UnitOfFrequency.HERTZ, "l1", "frequency"),
        PowerWatchdogLineSensor(manager, "L1 Output Voltage", SensorDeviceClass.VOLTAGE,
                               UnitOfElectricPotential.VOLT, "l1", "output_voltage"),

        # ── L2 (50A only — unavailable on 30A models) ──────────────────────
        PowerWatchdogLineSensor(manager, "L2 Voltage", SensorDeviceClass.VOLTAGE,
                               UnitOfElectricPotential.VOLT, "l2", "voltage"),
        PowerWatchdogLineSensor(manager, "L2 Current", SensorDeviceClass.CURRENT,
                               UnitOfElectricCurrent.AMPERE, "l2", "current"),
        PowerWatchdogLineSensor(manager, "L2 Power", SensorDeviceClass.POWER,
                               UnitOfPower.WATT, "l2", "power"),
        PowerWatchdogLineSensor(manager, "L2 Energy", SensorDeviceClass.ENERGY,
                               UnitOfEnergy.KILO_WATT_HOUR, "l2", "energy",
                               state_class=SensorStateClass.TOTAL_INCREASING),
        PowerWatchdogLineSensor(manager, "L2 Frequency", SensorDeviceClass.FREQUENCY,
                               UnitOfFrequency.HERTZ, "l2", "frequency"),
        PowerWatchdogLineSensor(manager, "L2 Output Voltage", SensorDeviceClass.VOLTAGE,
                               UnitOfElectricPotential.VOLT, "l2", "output_voltage"),

        # ── Totals ──────────────────────────────────────────────────────────
        PowerWatchdogTotalSensor(manager, "Total Power", SensorDeviceClass.POWER,
                                 UnitOfPower.WATT, "power"),
        PowerWatchdogTotalSensor(manager, "Total Energy", SensorDeviceClass.ENERGY,
                                 UnitOfEnergy.KILO_WATT_HOUR, "energy",
                                 state_class=SensorStateClass.TOTAL_INCREASING),

        # ── Error codes ────────────────────────────────────────────────────
        PowerWatchdogErrorSensor(manager, "L1 Error Code", "l1"),
        PowerWatchdogErrorSensor(manager, "L2 Error Code", "l2"),
        PowerWatchdogCombinedErrorSensor(manager, "Error Code"),

        # ── Boost status ───────────────────────────────────────────────────
        PowerWatchdogLineSensor(manager, "L1 Boost", None, None, "l1", "boost",
                               state_class=None),
        PowerWatchdogLineSensor(manager, "L2 Boost", None, None, "l2", "boost",
                               state_class=None),

        # ── Temperature (E8/V8 models only) ───────────────────────────────
        PowerWatchdogTemperatureSensor(manager, "L1 Temperature",
                                      SensorDeviceClass.TEMPERATURE,
                                      UnitOfTemperature.CELSIUS, "l1", "temperature"),
        PowerWatchdogTemperatureSensor(manager, "L2 Temperature",
                                      SensorDeviceClass.TEMPERATURE,
                                      UnitOfTemperature.CELSIUS, "l2", "temperature"),

        # ── Device status ──────────────────────────────────────────────────
        PowerWatchdogLineSensor(manager, "L1 Status", None, None, "l1", "status",
                               state_class=None),
        PowerWatchdogLineSensor(manager, "L2 Status", None, None, "l2", "status",
                               state_class=None),
    ]

    async_add_entities(sensors)


class PowerWatchdogLineSensor(SensorEntity):
    """Sensor bound to a single AC line (L1 or L2)."""

    _attr_should_poll = False

    def __init__(
        self,
        manager: PowerWatchdogManager,
        name_suffix: str,
        device_class: SensorDeviceClass,
        unit: str,
        line: str,
        field: str,
        *,
        state_class: SensorStateClass = SensorStateClass.MEASUREMENT,
    ) -> None:
        self._manager = manager
        self._line = line  # "l1" or "l2"
        self._field = field
        self._attr_name = f"{manager.name} {name_suffix}"
        self._attr_unique_id = f"{manager.address}_{line}_{field}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class
        self._attr_device_info = _device_info(manager)
        manager.register_sensor(self)

    @property
    def available(self) -> bool:
        """L2 sensors are unavailable until 50A dual-line data arrives."""
        if self._line == "l2" and not self._manager.data.has_l2:
            return False
        line_data = getattr(self._manager.data, self._line, None)
        return line_data is not None and getattr(line_data, self._field) is not None

    @property
    def native_value(self) -> float | int | None:
        """Return the current sensor value."""
        line_data = getattr(self._manager.data, self._line, None)
        if line_data is None:
            return None
        return getattr(line_data, self._field, None)


class PowerWatchdogTemperatureSensor(PowerWatchdogLineSensor):
    """Temperature sensor — only available on E8/V8 hardware."""

    @property
    def available(self) -> bool:
        """Unavailable when the device model does not support temperature."""
        if not self._manager.has_temperature:
            return False
        return super().available


class PowerWatchdogTotalSensor(SensorEntity):
    """Sensor that sums L1 + L2 for combined totals."""

    _attr_should_poll = False

    def __init__(
        self,
        manager: PowerWatchdogManager,
        name_suffix: str,
        device_class: SensorDeviceClass,
        unit: str,
        field: str,
        *,
        state_class: SensorStateClass = SensorStateClass.MEASUREMENT,
    ) -> None:
        self._manager = manager
        self._field = field
        self._attr_name = f"{manager.name} {name_suffix}"
        self._attr_unique_id = f"{manager.address}_total_{field}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class
        self._attr_device_info = _device_info(manager)
        manager.register_sensor(self)

    @property
    def available(self) -> bool:
        """Available as long as L1 data exists."""
        return (
            self._manager.data.l1 is not None
            and getattr(self._manager.data.l1, self._field) is not None
        )

    @property
    def native_value(self) -> float | None:
        """Return L1 + L2 (or just L1 for 30A models)."""
        l1_val = getattr(self._manager.data.l1, self._field, None)
        if l1_val is None:
            return None
        total = l1_val
        if self._manager.data.has_l2:
            l2_val = getattr(self._manager.data.l2, self._field, None)
            if l2_val is not None:
                total = round(total + l2_val, 2)
        return total


class PowerWatchdogErrorSensor(SensorEntity):
    """Sensor for a per-line error code with human-readable attributes."""

    _attr_should_poll = False

    def __init__(
        self,
        manager: PowerWatchdogManager,
        name_suffix: str,
        line: str,
    ) -> None:
        self._manager = manager
        self._line = line  # "l1" or "l2"
        self._attr_name = f"{manager.name} {name_suffix}"
        self._attr_unique_id = f"{manager.address}_{line}_error_code"
        self._attr_icon = "mdi:alert-circle-outline"
        self._attr_device_info = _device_info(manager)
        manager.register_sensor(self)

    @property
    def available(self) -> bool:
        """L2 error sensor is unavailable until 50A data arrives."""
        if self._line == "l2" and not self._manager.data.has_l2:
            return False
        line_data = getattr(self._manager.data, self._line, None)
        return line_data is not None and line_data.error_code is not None

    @property
    def native_value(self) -> int | None:
        """Return the raw error code integer."""
        line_data = getattr(self._manager.data, self._line, None)
        if line_data is None:
            return None
        return line_data.error_code

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Include human-readable error title and description."""
        return _error_attributes(self.native_value)


class PowerWatchdogCombinedErrorSensor(SensorEntity):
    """Sensor that reports the worst (highest) error code across L1 and L2."""

    _attr_should_poll = False

    def __init__(
        self,
        manager: PowerWatchdogManager,
        name_suffix: str,
    ) -> None:
        self._manager = manager
        self._attr_name = f"{manager.name} {name_suffix}"
        self._attr_unique_id = f"{manager.address}_combined_error_code"
        self._attr_icon = "mdi:alert-circle-outline"
        self._attr_device_info = _device_info(manager)
        manager.register_sensor(self)

    @property
    def available(self) -> bool:
        """Available as long as L1 data exists."""
        return (
            self._manager.data.l1 is not None
            and self._manager.data.l1.error_code is not None
        )

    @property
    def native_value(self) -> int | None:
        """Return max(L1 error, L2 error) — or just L1 for 30A models."""
        l1 = self._manager.data.l1
        if l1 is None or l1.error_code is None:
            return None
        error_code = l1.error_code
        if self._manager.data.has_l2:
            l2 = self._manager.data.l2
            if l2 is not None and l2.error_code is not None:
                error_code = max(error_code, l2.error_code)
        return error_code

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Include human-readable error title and description."""
        return _error_attributes(self.native_value)
