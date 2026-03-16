"""Sensor platform for the Hughes Power Watchdog integration.

Sensor default visibility rules
─────────────────────────────────────────────────────────────────────────────
  Sensor                 30A default   50A default   Unknown default
  ─────────────────────  ───────────   ───────────   ───────────────
  L1 Voltage             enabled       enabled       enabled
  L1 Current             enabled       enabled       enabled
  L1 Power               enabled       enabled       enabled
  L1 Energy              enabled       enabled       enabled
  L1 Frequency           enabled       enabled       enabled
  L1 Output Voltage      disabled      disabled      disabled
  L1 Error Code          enabled       enabled       enabled
  L1 Error Description   enabled       enabled       enabled
  L2 Voltage             disabled      enabled       enabled
  L2 Current             disabled      enabled       enabled
  L2 Power               disabled      enabled       enabled
  L2 Energy              disabled      enabled       enabled
  L2 Frequency           disabled      enabled       enabled
  L2 Output Voltage      disabled      disabled      disabled
  L2 Error Code          disabled      enabled       enabled
  L2 Error Description   disabled      enabled       enabled
  Total Power            enabled       enabled       enabled
  Total Energy           enabled       enabled       enabled
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
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_BLE_NAME,
    DOMAIN,
    detect_line_count,
    error_code_display,
    error_description,
)
from .models import PowerWatchdogManager

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Power Watchdog sensor entities."""
    manager: PowerWatchdogManager = hass.data[DOMAIN][entry.entry_id]["manager"]

    ble_name: str = entry.data.get(CONF_BLE_NAME, "")
    line_count = detect_line_count(ble_name)

    _LOGGER.debug(
        "Setting up sensors — BLE name: '%s', detected line count: %s",
        ble_name,
        line_count,
    )

    l2_enabled = line_count in ("dual", "unknown")

    if line_count == "unknown":
        _LOGGER.warning(
            "BLE name '%s' was not recognised as a known Power Watchdog model. "
            "All sensors will be enabled by default. Please open an issue at "
            "https://github.com/jdaleo23/ha-power-watchdog with your device "
            "name so it can be added to the compatibility list.",
            ble_name,
        )

    sensors: list[SensorEntity] = [
        # ── L1 — always enabled ──────────────────────────────────────────────
        PowerWatchdogLineSensor(
            manager, "L1 Voltage", SensorDeviceClass.VOLTAGE,
            UnitOfElectricPotential.VOLT, "l1", "voltage",
        ),
        PowerWatchdogLineSensor(
            manager, "L1 Current", SensorDeviceClass.CURRENT,
            UnitOfElectricCurrent.AMPERE, "l1", "current",
        ),
        PowerWatchdogLineSensor(
            manager, "L1 Power", SensorDeviceClass.POWER,
            UnitOfPower.WATT, "l1", "power",
        ),
        PowerWatchdogLineSensor(
            manager, "L1 Energy", SensorDeviceClass.ENERGY,
            UnitOfEnergy.KILO_WATT_HOUR, "l1", "energy",
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        PowerWatchdogLineSensor(
            manager, "L1 Frequency", SensorDeviceClass.FREQUENCY,
            UnitOfFrequency.HERTZ, "l1", "frequency",
        ),

        # ── L1 Output Voltage — disabled for ALL models ──────────────────────
        PowerWatchdogLineSensor(
            manager, "L1 Output Voltage", SensorDeviceClass.VOLTAGE,
            UnitOfElectricPotential.VOLT, "l1", "output_voltage",
            enabled_by_default=False,
        ),

        # ── L1 Error sensors — always enabled ────────────────────────────────
        PowerWatchdogErrorCodeSensor(manager, "l1"),
        PowerWatchdogErrorDescriptionSensor(manager, "l1"),

        # ── L2 — enabled for 50A and unknown, disabled for confirmed 30A ─────
        PowerWatchdogLineSensor(
            manager, "L2 Voltage", SensorDeviceClass.VOLTAGE,
            UnitOfElectricPotential.VOLT, "l2", "voltage",
            enabled_by_default=l2_enabled,
        ),
        PowerWatchdogLineSensor(
            manager, "L2 Current", SensorDeviceClass.CURRENT,
            UnitOfElectricCurrent.AMPERE, "l2", "current",
            enabled_by_default=l2_enabled,
        ),
        PowerWatchdogLineSensor(
            manager, "L2 Power", SensorDeviceClass.POWER,
            UnitOfPower.WATT, "l2", "power",
            enabled_by_default=l2_enabled,
        ),
        PowerWatchdogLineSensor(
            manager, "L2 Energy", SensorDeviceClass.ENERGY,
            UnitOfEnergy.KILO_WATT_HOUR, "l2", "energy",
            state_class=SensorStateClass.TOTAL_INCREASING,
            enabled_by_default=l2_enabled,
        ),
        PowerWatchdogLineSensor(
            manager, "L2 Frequency", SensorDeviceClass.FREQUENCY,
            UnitOfFrequency.HERTZ, "l2", "frequency",
            enabled_by_default=l2_enabled,
        ),

        # ── L2 Output Voltage — disabled for ALL models ──────────────────────
        PowerWatchdogLineSensor(
            manager, "L2 Output Voltage", SensorDeviceClass.VOLTAGE,
            UnitOfElectricPotential.VOLT, "l2", "output_voltage",
            enabled_by_default=False,
        ),

        # ── L2 Error sensors — follow L2 default ─────────────────────────────
        PowerWatchdogErrorCodeSensor(manager, "l2", enabled_by_default=l2_enabled),
        PowerWatchdogErrorDescriptionSensor(manager, "l2", enabled_by_default=l2_enabled),

        # ── Totals — always enabled ──────────────────────────────────────────
        PowerWatchdogTotalSensor(
            manager, "Total Power", SensorDeviceClass.POWER,
            UnitOfPower.WATT, "power",
        ),
        PowerWatchdogTotalSensor(
            manager, "Total Energy", SensorDeviceClass.ENERGY,
            UnitOfEnergy.KILO_WATT_HOUR, "energy",
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
    ]

    async_add_entities(sensors)


# ── Shared device info helper ────────────────────────────────────────────────

def _device_info(manager: PowerWatchdogManager) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, manager.address)},
        name=manager.name,
        manufacturer="Hughes Autoformers",
        model="Power Watchdog",
    )


# ── Sensor classes ───────────────────────────────────────────────────────────

class PowerWatchdogLineSensor(SensorEntity):
    """Sensor bound to a single field on one AC line (L1 or L2)."""

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
        enabled_by_default: bool = True,
    ) -> None:
        self._manager = manager
        self._line = line
        self._field = field
        self._attr_name = f"{manager.name} {name_suffix}"
        self._attr_unique_id = f"{manager.address}_{line}_{field}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class
        self._attr_entity_registry_enabled_default = enabled_by_default
        self._attr_device_info = _device_info(manager)
        manager.register_sensor(self)

    @property
    def available(self) -> bool:
        if self._line == "l2" and not self._manager.data.has_l2:
            return False
        line_data = getattr(self._manager.data, self._line, None)
        return line_data is not None and getattr(line_data, self._field) is not None

    @property
    def native_value(self) -> float | int | None:
        line_data = getattr(self._manager.data, self._line, None)
        if line_data is None:
            return None
        return getattr(line_data, self._field, None)


class PowerWatchdogErrorCodeSensor(SensorEntity):
    """Sensor reporting the short error code string (e.g. 'E3', 'OK')."""

    _attr_should_poll = False
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(
        self,
        manager: PowerWatchdogManager,
        line: str,
        *,
        enabled_by_default: bool = True,
    ) -> None:
        self._manager = manager
        self._line = line
        label = line.upper()
        self._attr_name = f"{manager.name} {label} Error Code"
        self._attr_unique_id = f"{manager.address}_{line}_error_code"
        self._attr_entity_registry_enabled_default = enabled_by_default
        self._attr_device_info = _device_info(manager)
        manager.register_sensor(self)

    @property
    def available(self) -> bool:
        if self._line == "l2" and not self._manager.data.has_l2:
            return False
        line_data = getattr(self._manager.data, self._line, None)
        return line_data is not None and line_data.error_code is not None

    @property
    def native_value(self) -> str | None:
        line_data = getattr(self._manager.data, self._line, None)
        if line_data is None:
            return None
        return error_code_display(line_data.error_code)


class PowerWatchdogErrorDescriptionSensor(SensorEntity):
    """Sensor reporting the full human-readable error description."""

    _attr_should_poll = False
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(
        self,
        manager: PowerWatchdogManager,
        line: str,
        *,
        enabled_by_default: bool = True,
    ) -> None:
        self._manager = manager
        self._line = line
        label = line.upper()
        self._attr_name = f"{manager.name} {label} Error Description"
        self._attr_unique_id = f"{manager.address}_{line}_error_description"
        self._attr_entity_registry_enabled_default = enabled_by_default
        self._attr_device_info = _device_info(manager)
        manager.register_sensor(self)

    @property
    def available(self) -> bool:
        if self._line == "l2" and not self._manager.data.has_l2:
            return False
        line_data = getattr(self._manager.data, self._line, None)
        return line_data is not None and line_data.error_code is not None

    @property
    def native_value(self) -> str | None:
        line_data = getattr(self._manager.data, self._line, None)
        if line_data is None:
            return None
        return error_description(line_data.error_code)


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
        return (
            self._manager.data.l1 is not None
            and getattr(self._manager.data.l1, self._field) is not None
        )

    @property
    def native_value(self) -> float | None:
        l1_val = getattr(self._manager.data.l1, self._field, None)
        if l1_val is None:
            return None
        total = l1_val
        if self._manager.data.has_l2:
            l2_val = getattr(self._manager.data.l2, self._field, None)
            if l2_val is not None:
                total = round(total + l2_val, 2)
        return total
