"""Test fixtures and Home Assistant module mocks.

The custom component imports from homeassistant.*, bleak, and
bleak_retry_connector.  We mock all of those at the sys.modules level
so the component code can be imported in a plain pytest environment
without a running Home Assistant instance.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest


# ── Mock Home Assistant and BLE libraries ───────────────────────────────────
# These must be installed in sys.modules *before* any component code is
# imported, because Python resolves top-level imports at module load time.


class _SensorEntityBase:
    """Minimal stand-in for homeassistant.components.sensor.SensorEntity."""

    _attr_should_poll: bool = True
    _attr_name: str = ""
    _attr_unique_id: str = ""
    _attr_device_class = None
    _attr_native_unit_of_measurement = None
    _attr_state_class = None
    _attr_device_info = None

    def async_write_ha_state(self) -> None:  # noqa: ANN101
        pass


class _ButtonEntityBase:
    """Minimal stand-in for homeassistant.components.button.ButtonEntity."""

    _attr_name: str = ""
    _attr_unique_id: str = ""
    _attr_icon: str = ""
    _attr_device_class = None
    _attr_device_info = None


def _install_mocks() -> None:
    """Populate sys.modules with mocks for all HA / BLE dependencies."""
    module_names = [
        "homeassistant",
        "homeassistant.core",
        "homeassistant.config_entries",
        "homeassistant.const",
        "homeassistant.components",
        "homeassistant.components.bluetooth",
        "homeassistant.components.sensor",
        "homeassistant.components.button",
        "homeassistant.helpers",
        "homeassistant.helpers.entity",
        "homeassistant.helpers.entity_platform",
        "homeassistant.helpers.selector",
        "bleak",
        "bleak_retry_connector",
        "voluptuous",
    ]
    for name in module_names:
        sys.modules.setdefault(name, MagicMock())

    # @callback must be a passthrough decorator so methods remain callable
    sys.modules["homeassistant.core"].callback = lambda fn: fn

    # SensorEntity / ButtonEntity must be real classes (subclassed in sensor.py)
    sensor_mod = sys.modules["homeassistant.components.sensor"]
    sensor_mod.SensorEntity = _SensorEntityBase
    sensor_mod.SensorDeviceClass = MagicMock()
    sensor_mod.SensorStateClass = MagicMock()

    button_mod = sys.modules["homeassistant.components.button"]
    button_mod.ButtonEntity = _ButtonEntityBase

    # ConfigEntry used as type hint and base class argument in config_flow
    sys.modules["homeassistant.config_entries"].ConfigEntry = MagicMock
    sys.modules["homeassistant.config_entries"].ConfigFlow = type(
        "ConfigFlow", (), {"__init_subclass__": classmethod(lambda cls, **kw: None)}
    )

    # Const values used at import time
    const_mod = sys.modules["homeassistant.const"]
    const_mod.CONF_ADDRESS = "address"
    const_mod.Platform = MagicMock()

    # DeviceInfo must accept keyword arguments
    sys.modules["homeassistant.helpers.entity"].DeviceInfo = lambda **kw: kw


_install_mocks()

# Ensure the project root is on sys.path so `custom_components` is importable
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


# ── Shared fixtures ─────────────────────────────────────────────────────────

from custom_components.hughes_power_watchdog.models import (  # noqa: E402
    PowerWatchdogManager,
)


@pytest.fixture()
def manager() -> PowerWatchdogManager:
    """Return a PowerWatchdogManager with a mocked HomeAssistant instance."""
    hass = MagicMock()
    mgr = PowerWatchdogManager(hass, "AA:BB:CC:DD:EE:FF", "Test Watchdog")
    return mgr
