"""Tests for Power Watchdog sensor entities.

Covers PowerWatchdogLineSensor availability, native_value retrieval,
and PowerWatchdogTotalSensor aggregation logic.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.helpers import build_30a_packet, build_50a_packet
from custom_components.hughes_power_watchdog.models import (
    LineData,
    PowerWatchdogManager,
    WatchdogData,
)
from custom_components.hughes_power_watchdog.sensor import (
    PowerWatchdogLineSensor,
    PowerWatchdogTotalSensor,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def manager() -> PowerWatchdogManager:
    """Fresh manager with no data yet."""
    hass = MagicMock()
    return PowerWatchdogManager(hass, "AA:BB:CC:DD:EE:FF", "Test Watchdog")


@pytest.fixture()
def manager_30a(manager: PowerWatchdogManager) -> PowerWatchdogManager:
    """Manager with a 30A (single-line) data update applied."""
    pkt = build_30a_packet(voltage=121.5, current=2.03, power=203.0, energy=500.0)
    manager._notification_handler(None, bytearray(pkt))
    return manager


@pytest.fixture()
def manager_50a(manager: PowerWatchdogManager) -> PowerWatchdogManager:
    """Manager with a 50A (dual-line) data update applied."""
    pkt = build_50a_packet(
        l1_voltage=121.5, l1_current=2.03, l1_power=203.0, l1_energy=500.0,
        l2_voltage=122.7, l2_current=0.36, l2_power=7.0, l2_energy=100.0,
    )
    manager._notification_handler(None, bytearray(pkt))
    return manager


def _make_line_sensor(
    mgr: PowerWatchdogManager,
    line: str = "l1",
    field: str = "voltage",
) -> PowerWatchdogLineSensor:
    """Create a LineSensor without triggering real HA entity setup."""
    sensor = PowerWatchdogLineSensor(
        mgr,
        name_suffix=f"{line.upper()} {field.title()}",
        device_class=MagicMock(),
        unit="V",
        line=line,
        field=field,
    )
    return sensor


def _make_total_sensor(
    mgr: PowerWatchdogManager,
    field: str = "power",
) -> PowerWatchdogTotalSensor:
    """Create a TotalSensor without triggering real HA entity setup."""
    sensor = PowerWatchdogTotalSensor(
        mgr,
        name_suffix=f"Total {field.title()}",
        device_class=MagicMock(),
        unit="W",
        field=field,
    )
    return sensor


# ── PowerWatchdogLineSensor tests ────────────────────────────────────────────


class TestLineSensorAvailability:
    """Tests for the `available` property of line sensors."""

    def test_l1_unavailable_before_data(self, manager: PowerWatchdogManager):
        """L1 sensor is unavailable when no data has arrived."""
        sensor = _make_line_sensor(manager, line="l1", field="voltage")
        assert sensor.available is False

    def test_l1_available_after_30a_data(self, manager_30a: PowerWatchdogManager):
        """L1 sensor is available after a 30A update."""
        sensor = _make_line_sensor(manager_30a, line="l1", field="voltage")
        assert sensor.available is True

    def test_l2_unavailable_on_30a(self, manager_30a: PowerWatchdogManager):
        """L2 sensor is unavailable on a 30A single-line model."""
        sensor = _make_line_sensor(manager_30a, line="l2", field="voltage")
        assert sensor.available is False

    def test_l2_available_on_50a(self, manager_50a: PowerWatchdogManager):
        """L2 sensor is available on a 50A dual-line model."""
        sensor = _make_line_sensor(manager_50a, line="l2", field="voltage")
        assert sensor.available is True

    def test_l1_available_on_50a(self, manager_50a: PowerWatchdogManager):
        """L1 sensor is available on a 50A model."""
        sensor = _make_line_sensor(manager_50a, line="l1", field="voltage")
        assert sensor.available is True


class TestLineSensorValue:
    """Tests for the `native_value` property of line sensors."""

    def test_l1_voltage_value(self, manager_30a: PowerWatchdogManager):
        """L1 voltage returns the parsed value."""
        sensor = _make_line_sensor(manager_30a, line="l1", field="voltage")
        assert sensor.native_value == 121.5

    def test_l1_current_value(self, manager_30a: PowerWatchdogManager):
        """L1 current returns the parsed value."""
        sensor = _make_line_sensor(manager_30a, line="l1", field="current")
        assert sensor.native_value == 2.03

    def test_l1_power_value(self, manager_30a: PowerWatchdogManager):
        """L1 power returns the parsed value."""
        sensor = _make_line_sensor(manager_30a, line="l1", field="power")
        assert sensor.native_value == 203.0

    def test_l1_energy_value(self, manager_30a: PowerWatchdogManager):
        """L1 energy returns the parsed value."""
        sensor = _make_line_sensor(manager_30a, line="l1", field="energy")
        assert sensor.native_value == 500.0

    def test_l2_voltage_value(self, manager_50a: PowerWatchdogManager):
        """L2 voltage returns the parsed value on a 50A model."""
        sensor = _make_line_sensor(manager_50a, line="l2", field="voltage")
        assert sensor.native_value == 122.7

    def test_l2_current_value(self, manager_50a: PowerWatchdogManager):
        """L2 current returns the parsed value on a 50A model."""
        sensor = _make_line_sensor(manager_50a, line="l2", field="current")
        assert sensor.native_value == 0.36

    def test_l2_power_value(self, manager_50a: PowerWatchdogManager):
        """L2 power returns the parsed value on a 50A model."""
        sensor = _make_line_sensor(manager_50a, line="l2", field="power")
        assert sensor.native_value == 7.0

    def test_returns_none_before_data(self, manager: PowerWatchdogManager):
        """native_value is None when no data has arrived."""
        sensor = _make_line_sensor(manager, line="l1", field="voltage")
        assert sensor.native_value is None

    def test_all_line_fields(self, manager_50a: PowerWatchdogManager):
        """Verify every field on both lines returns a non-None value."""
        for line in ("l1", "l2"):
            for field in ("voltage", "current", "power", "energy",
                          "output_voltage", "frequency"):
                sensor = _make_line_sensor(manager_50a, line=line, field=field)
                assert sensor.native_value is not None, (
                    f"{line}.{field} should not be None"
                )


class TestLineSensorAttributes:
    """Tests for sensor attribute setup."""

    def test_unique_id_format(self, manager: PowerWatchdogManager):
        """unique_id follows the {address}_{line}_{field} pattern."""
        sensor = _make_line_sensor(manager, line="l1", field="voltage")
        assert sensor._attr_unique_id == "AA:BB:CC:DD:EE:FF_l1_voltage"

    def test_name_format(self, manager: PowerWatchdogManager):
        """Entity name includes the device name and sensor description."""
        sensor = _make_line_sensor(manager, line="l1", field="voltage")
        assert "Test Watchdog" in sensor._attr_name

    def test_should_poll_disabled(self, manager: PowerWatchdogManager):
        """Line sensors are push-based (no polling)."""
        sensor = _make_line_sensor(manager, line="l1", field="voltage")
        assert sensor._attr_should_poll is False


# ── PowerWatchdogTotalSensor tests ───────────────────────────────────────────


class TestTotalSensorAvailability:
    """Tests for the `available` property of total sensors."""

    def test_unavailable_before_data(self, manager: PowerWatchdogManager):
        """Total sensor is unavailable when no data has arrived."""
        sensor = _make_total_sensor(manager, field="power")
        assert sensor.available is False

    def test_available_with_30a_data(self, manager_30a: PowerWatchdogManager):
        """Total sensor is available after a 30A update."""
        sensor = _make_total_sensor(manager_30a, field="power")
        assert sensor.available is True

    def test_available_with_50a_data(self, manager_50a: PowerWatchdogManager):
        """Total sensor is available after a 50A update."""
        sensor = _make_total_sensor(manager_50a, field="power")
        assert sensor.available is True


class TestTotalSensorValue:
    """Tests for the `native_value` property of total sensors."""

    def test_30a_total_equals_l1(self, manager_30a: PowerWatchdogManager):
        """On a 30A model, total power == L1 power."""
        sensor = _make_total_sensor(manager_30a, field="power")
        assert sensor.native_value == 203.0

    def test_50a_total_sums_lines(self, manager_50a: PowerWatchdogManager):
        """On a 50A model, total power == L1 + L2."""
        sensor = _make_total_sensor(manager_50a, field="power")
        # L1=203.0 + L2=7.0 = 210.0
        assert sensor.native_value == 210.0

    def test_30a_total_energy_equals_l1(self, manager_30a: PowerWatchdogManager):
        """On a 30A model, total energy == L1 energy."""
        sensor = _make_total_sensor(manager_30a, field="energy")
        assert sensor.native_value == 500.0

    def test_50a_total_energy_sums_lines(self, manager_50a: PowerWatchdogManager):
        """On a 50A model, total energy == L1 + L2."""
        sensor = _make_total_sensor(manager_50a, field="energy")
        # L1=500.0 + L2=100.0 = 600.0
        assert sensor.native_value == 600.0

    def test_returns_none_before_data(self, manager: PowerWatchdogManager):
        """native_value is None when no data has arrived."""
        sensor = _make_total_sensor(manager, field="power")
        assert sensor.native_value is None


class TestTotalSensorAttributes:
    """Tests for total sensor attribute setup."""

    def test_unique_id_format(self, manager: PowerWatchdogManager):
        """unique_id follows the {address}_total_{field} pattern."""
        sensor = _make_total_sensor(manager, field="power")
        assert sensor._attr_unique_id == "AA:BB:CC:DD:EE:FF_total_power"

    def test_should_poll_disabled(self, manager: PowerWatchdogManager):
        """Total sensors are push-based (no polling)."""
        sensor = _make_total_sensor(manager, field="power")
        assert sensor._attr_should_poll is False


# ── Integration scenario tests ───────────────────────────────────────────────


class TestEndToEnd:
    """Higher-level scenarios combining manager + sensors."""

    def test_30a_to_50a_transition(self, manager: PowerWatchdogManager):
        """A device that initially sends 30A data, then 50A, correctly transitions."""
        l2_sensor = _make_line_sensor(manager, line="l2", field="voltage")

        # Start with 30A
        pkt_30a = build_30a_packet(voltage=121.0)
        manager._notification_handler(None, bytearray(pkt_30a))
        assert l2_sensor.available is False

        # Transition to 50A
        pkt_50a = build_50a_packet(l1_voltage=121.5, l2_voltage=122.7)
        manager._notification_handler(None, bytearray(pkt_50a))
        assert l2_sensor.available is True
        assert l2_sensor.native_value == 122.7

    def test_continuous_updates_reflect_latest(self, manager: PowerWatchdogManager):
        """Successive updates overwrite data; sensor always returns latest."""
        sensor = _make_line_sensor(manager, line="l1", field="voltage")

        for v in (120.0, 121.0, 122.0, 119.5):
            pkt = build_30a_packet(voltage=v)
            manager._notification_handler(None, bytearray(pkt))
            assert sensor.native_value == v

    def test_total_tracks_changes(self, manager: PowerWatchdogManager):
        """Total sensor updates as new data arrives."""
        total_sensor = _make_total_sensor(manager, field="power")

        # 30A update
        pkt1 = build_30a_packet(power=200.0)
        manager._notification_handler(None, bytearray(pkt1))
        assert total_sensor.native_value == 200.0

        # 50A update
        pkt2 = build_50a_packet(l1_power=200.0, l2_power=150.0)
        manager._notification_handler(None, bytearray(pkt2))
        assert total_sensor.native_value == 350.0

    def test_sensor_registered_with_manager(self, manager: PowerWatchdogManager):
        """Creating a sensor registers it with the manager."""
        initial_count = len(manager.sensors)
        _make_line_sensor(manager, line="l1", field="voltage")
        assert len(manager.sensors) == initial_count + 1

    def test_multiple_sensors_all_registered(self, manager: PowerWatchdogManager):
        """Multiple sensors all get registered."""
        _make_line_sensor(manager, line="l1", field="voltage")
        _make_line_sensor(manager, line="l1", field="current")
        _make_total_sensor(manager, field="power")
        assert len(manager.sensors) == 3
