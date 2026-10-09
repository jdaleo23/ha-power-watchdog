"""Tests for the Power Watchdog fault binary sensor.

Covers PowerWatchdogFaultSensor availability (including the BLE connection
gate) and is_on logic.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.helpers import build_30a_packet, build_50a_packet
from custom_components.hughes_power_watchdog.binary_sensor import (
    PowerWatchdogFaultSensor,
)
from custom_components.hughes_power_watchdog.models import PowerWatchdogManager


@pytest.fixture()
def manager() -> PowerWatchdogManager:
    """Fresh manager with no data yet, with an active (connected) BLE client."""
    hass = MagicMock()
    mgr = PowerWatchdogManager(hass, "AA:BB:CC:DD:EE:FF", "Test Watchdog")
    mgr.client = MagicMock(is_connected=True)
    return mgr


@pytest.fixture()
def manager_30a(manager: PowerWatchdogManager) -> PowerWatchdogManager:
    """Manager with a 30A (single-line), fault-free data update applied."""
    pkt = build_30a_packet(error=0)
    manager._protocol.notification_handler(None, bytearray(pkt))
    return manager


class TestFaultSensorAvailability:
    """Tests for the `available` property, including the connection gate."""

    def test_unavailable_before_data(self, manager: PowerWatchdogManager):
        sensor = PowerWatchdogFaultSensor(manager, "l1")
        assert sensor.available is False

    def test_available_after_data(self, manager_30a: PowerWatchdogManager):
        sensor = PowerWatchdogFaultSensor(manager_30a, "l1")
        assert sensor.available is True

    def test_l2_unavailable_on_30a(self, manager_30a: PowerWatchdogManager):
        sensor = PowerWatchdogFaultSensor(manager_30a, "l2")
        assert sensor.available is False

    def test_l2_available_on_50a(self, manager: PowerWatchdogManager):
        pkt = build_50a_packet()
        manager._protocol.notification_handler(None, bytearray(pkt))
        sensor = PowerWatchdogFaultSensor(manager, "l2")
        assert sensor.available is True

    def test_unavailable_when_disconnected(self, manager_30a: PowerWatchdogManager):
        """Fault sensor goes unavailable when the BLE connection drops."""
        sensor = PowerWatchdogFaultSensor(manager_30a, "l1")
        assert sensor.available is True

        manager_30a.client.is_connected = False
        assert sensor.available is False

    def test_unavailable_with_no_client(self, manager_30a: PowerWatchdogManager):
        sensor = PowerWatchdogFaultSensor(manager_30a, "l1")
        manager_30a.client = None
        assert sensor.available is False


class TestFaultSensorIsOn:
    """Tests for the `is_on` property."""

    def test_off_when_no_error(self, manager_30a: PowerWatchdogManager):
        sensor = PowerWatchdogFaultSensor(manager_30a, "l1")
        assert sensor.is_on is False

    def test_on_when_error(self, manager: PowerWatchdogManager):
        pkt = build_30a_packet(error=3)
        manager._protocol.notification_handler(None, bytearray(pkt))
        sensor = PowerWatchdogFaultSensor(manager, "l1")
        assert sensor.is_on is True

    def test_none_before_data(self, manager: PowerWatchdogManager):
        sensor = PowerWatchdogFaultSensor(manager, "l1")
        assert sensor.is_on is None

    def test_is_on_ignores_connection_state(self, manager_30a: PowerWatchdogManager):
        """is_on reflects last-known fault state regardless of connection —
        only `available` gates on the BLE connection."""
        sensor = PowerWatchdogFaultSensor(manager_30a, "l1")
        manager_30a.client.is_connected = False
        assert sensor.is_on is False
