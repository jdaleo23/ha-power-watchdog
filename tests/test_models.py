"""Tests for PowerWatchdogManager connection-state plumbing.

Covers `is_connected` and the disconnect callback — specifically that a
BLE disconnect pushes an immediate state update to registered sensors
instead of leaving them frozen at their last-known value until the next
piece of telemetry arrives (which may be a long time, or never, if the
device stays offline).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.hughes_power_watchdog.models import PowerWatchdogManager


@pytest.fixture()
def manager() -> PowerWatchdogManager:
    hass = MagicMock()
    return PowerWatchdogManager(hass, "AA:BB:CC:DD:EE:FF", "Test Watchdog")


class TestIsConnected:
    def test_false_with_no_client(self, manager: PowerWatchdogManager):
        assert manager.is_connected is False

    def test_false_when_client_reports_disconnected(
        self, manager: PowerWatchdogManager
    ):
        manager.client = MagicMock(is_connected=False)
        assert manager.is_connected is False

    def test_true_when_client_reports_connected(
        self, manager: PowerWatchdogManager
    ):
        manager.client = MagicMock(is_connected=True)
        assert manager.is_connected is True


class TestOnDisconnected:
    """`_on_disconnected` must push a state update immediately, not rely on
    the next telemetry packet (which may never come) to refresh `available`."""

    def test_notifies_registered_sensors(self, manager: PowerWatchdogManager):
        sensor = MagicMock()
        manager.register_sensor(sensor)

        manager._on_disconnected(None)

        sensor.async_write_ha_state.assert_called_once()

    def test_notifies_all_registered_sensors(self, manager: PowerWatchdogManager):
        sensor1 = MagicMock()
        sensor2 = MagicMock()
        manager.register_sensor(sensor1)
        manager.register_sensor(sensor2)

        manager._on_disconnected(None)

        sensor1.async_write_ha_state.assert_called_once()
        sensor2.async_write_ha_state.assert_called_once()

    def test_skips_sensors_with_no_hass(self, manager: PowerWatchdogManager):
        """notify_sensors already guards on `sensor.hass` — confirm
        _on_disconnected goes through that same path rather than calling
        async_write_ha_state unconditionally."""
        sensor = MagicMock()
        sensor.hass = None
        manager.register_sensor(sensor)

        manager._on_disconnected(None)

        sensor.async_write_ha_state.assert_not_called()
