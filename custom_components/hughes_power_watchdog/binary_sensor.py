"""Binary sensor platform for the Hughes Power Watchdog integration.

Provides a Fault Active binary sensor per line (L1 / L2).
  * ON  - an error code is active (E1-E9, F1-F2)
  * OFF - no fault (error code == 0)

Useful for automations, alerts, and dashboard badges.
"""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_BLE_NAME, DOMAIN, detect_line_count
from .device_info import build_device_info
from .models import PowerWatchdogManager

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Power Watchdog binary sensor entities."""
    manager: PowerWatchdogManager = hass.data[DOMAIN][entry.entry_id]["manager"]

    ble_name: str = entry.data.get(CONF_BLE_NAME, "")
    line_count = detect_line_count(ble_name)
    l2_enabled = line_count in ("dual", "unknown")

    async_add_entities([
        PowerWatchdogFaultSensor(manager, "l1", enabled_by_default=True),
        PowerWatchdogFaultSensor(manager, "l2", enabled_by_default=l2_enabled),
    ])


class PowerWatchdogFaultSensor(BinarySensorEntity):
    """Binary sensor that is ON when an error code is active on a line."""

    _attr_should_poll = False
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

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
        self._attr_name = f"{manager.name} {label} Fault Active"
        self._attr_unique_id = f"{manager.address}_{line}_fault_active"
        self._attr_entity_registry_enabled_default = enabled_by_default
        self._attr_device_info = build_device_info(manager)
        manager.register_sensor(self)

    @property
    def available(self) -> bool:
        if self._line == "l2" and not self._manager.data.has_l2:
            return False
        line_data = getattr(self._manager.data, self._line, None)
        return line_data is not None and line_data.error_code is not None

    @property
    def is_on(self) -> bool | None:
        """Return True if an error code is active (non-zero)."""
        line_data = getattr(self._manager.data, self._line, None)
        if line_data is None or line_data.error_code is None:
            return None
        return line_data.error_code != 0
