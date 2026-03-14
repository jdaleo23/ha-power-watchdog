"""Sensor platform for the Hughes Power Watchdog integration.

Sensor default visibility rules
─────────────────────────────────────────────────────────────────────────────
Model tier is determined at setup time from the raw BLE advertisement name
stored as CONF_BLE_NAME (e.g. "WD_V6_4af6ee9d9d05") — NOT the user-supplied
friendly name. Runtime data (has_l2) confirms this once packets arrive.

  Sensor                 30A default   50A default   Unknown default
  ─────────────────────  ───────────   ───────────   ───────────────
  L1 Voltage             enabled       enabled       enabled
  L1 Current             enabled       enabled       enabled
  L1 Power               enabled       enabled       enabled
  L1 Energy              enabled       enabled       enabled
  L1 Frequency           enabled       enabled       enabled
  L1 Output Voltage      disabled      disabled      disabled  *
  L2 Voltage             disabled      enabled       enabled
  L2 Current             disabled      enabled       enabled
  L2 Power               disabled      enabled       enabled
  L2 Energy              disabled      enabled       enabled
  L2 Frequency           disabled      enabled       enabled
  L2 Output Voltage      disabled      disabled      disabled  *
  Total Power            enabled       enabled       enabled
  Total Energy           enabled       enabled       enabled

* Output Voltage (offset 20) is disabled for all models. On WD_V6 hardware
  it was confirmed to mirror the energy counter rather than report a real
  voltage. May be valid on voltage-booster variants — enable manually if
  needed in Settings → Devices & Services.
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

from .const import CONF_BLE_NAME, DOMAIN, detect_line_count
from .models import PowerWatchdogManager

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Power Watchdog sensor entities."""
    manager: PowerWatchdogManager = hass.data[DOMAIN][entry.entry_id]["manager"]

    # Use the raw BLE advertisement name for model detection — NOT the
    # user-supplied friendly name which won't match any known model format.
    ble_name: str = entry.data.get(CONF_BLE_NAME, "")
    line_count = detect_line_count(ble_name)

    _LOGGER.debug(
        "Setting up sensors — BLE name: '%s', detected line count: %s",
        ble_name,
        line_count,
    )

    # L2 sensors enabled for confirmed 50A models AND unknown devices.
    # Unknown devices get everything enabled so the user can see all data
    # and disable what doesn't apply to their hardware.
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
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, manager.address)},
            name=manager.name,
            manufacturer="Hughes Autoformers",
            model="Power Watchdog",
        )
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
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, manager.address)},
            name=manager.name,
            manufacturer="Hughes Autoformers",
            model="Power Watchdog",
        )
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
