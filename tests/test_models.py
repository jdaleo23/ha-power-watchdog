"""Tests for PowerWatchdogManager connection-state plumbing.

Covers `is_connected` and the disconnect callback — specifically that a
BLE disconnect pushes an immediate state update to registered sensors
instead of leaving them frozen at their last-known value until the next
piece of telemetry arrives (which may be a long time, or never, if the
device stays offline). Also covers the per-connection reset, and one real
pass through `connect_loop` with the BLE layer mocked out.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.helpers import build_30a_packet, build_50a_packet
from custom_components.hughes_power_watchdog import models
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


class TestResetForNewConnection:
    """Readings from a previous connection are dropped on reconnect, but the
    learned line topology is not."""

    def test_clears_readings(self, manager: PowerWatchdogManager):
        pkt = build_50a_packet(l1_voltage=121.5, l2_voltage=122.7)
        manager._protocol.notification_handler(None, bytearray(pkt))

        manager._reset_for_new_connection()

        assert manager.data.l1.voltage is None
        assert manager.data.l2.voltage is None

    def test_keeps_has_l2(self, manager: PowerWatchdogManager):
        pkt = build_50a_packet()
        manager._protocol.notification_handler(None, bytearray(pkt))
        assert manager.data.has_l2 is True

        manager._reset_for_new_connection()
        assert manager.data.has_l2 is True

    def test_single_line_stays_single_line(self, manager: PowerWatchdogManager):
        pkt = build_30a_packet()
        manager._protocol.notification_handler(None, bytearray(pkt))

        manager._reset_for_new_connection()
        assert manager.data.has_l2 is False

    def test_clears_protocol_buffer(self, manager: PowerWatchdogManager):
        """Half a packet from the old connection must not be stitched onto
        bytes from the new one."""
        pkt = build_30a_packet(voltage=121.5)
        manager._protocol.notification_handler(None, bytearray(pkt[:10]))

        manager._reset_for_new_connection()
        manager._protocol.notification_handler(None, bytearray(pkt[10:]))

        assert manager.data.l1.voltage is None


class TestConnectLoop:
    """Drive one real pass of connect_loop with the BLE layer mocked out."""

    def _run_one_connection(
        self, manager: PowerWatchdogManager, client: MagicMock
    ) -> None:
        """Connect once, let the link drop, then cancel on the retry."""
        device = MagicMock()
        with (
            patch.object(
                models, "async_ble_device_from_address",
                side_effect=[device, asyncio.CancelledError()],
            ),
            patch.object(
                models, "establish_connection", AsyncMock(return_value=client)
            ),
        ):
            with pytest.raises(asyncio.CancelledError):
                asyncio.run(manager.connect_loop())

    @staticmethod
    def _client() -> MagicMock:
        # is_connected=False lets the "while connected" wait exit at once.
        client = MagicMock(is_connected=False)
        client.start_notify = AsyncMock()
        client.write_gatt_char = AsyncMock()
        client.disconnect = AsyncMock()
        return client

    def test_stale_readings_cleared_and_topology_kept(
        self, manager: PowerWatchdogManager
    ):
        pkt = build_50a_packet(l1_voltage=121.5, l2_voltage=122.7)
        manager._protocol.notification_handler(None, bytearray(pkt))

        self._run_one_connection(manager, self._client())

        assert manager.data.l1.voltage is None
        assert manager.data.has_l2 is True

    def test_subscribes_and_sends_handshake(self, manager: PowerWatchdogManager):
        client = self._client()
        self._run_one_connection(manager, client)

        client.start_notify.assert_awaited_once_with(
            manager._protocol.notify_uuid,
            manager._protocol.notification_handler,
        )
        client.write_gatt_char.assert_awaited_once()

    def test_sensors_notified_after_connecting(
        self, manager: PowerWatchdogManager
    ):
        sensor = MagicMock()
        manager.register_sensor(sensor)

        self._run_one_connection(manager, self._client())

        sensor.async_write_ha_state.assert_called()

    def test_disconnects_on_cancel(self, manager: PowerWatchdogManager):
        client = self._client()
        self._run_one_connection(manager, client)

        client.disconnect.assert_awaited_once()
