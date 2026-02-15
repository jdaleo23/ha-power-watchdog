"""Tests for the Power Watchdog reset button entity.

Covers button construction, CMD_RESET_ENERGY payload validation,
and async_press behaviour.
"""

from __future__ import annotations

import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hughes_power_watchdog.button import WatchdogResetButton
from custom_components.hughes_power_watchdog.const import (
    CHARACTERISTIC_UUID,
    CMD_RESET_ENERGY,
    HEADER_SIZE,
    PACKET_IDENTIFIER,
    PACKET_TAIL,
    TAIL_SIZE,
)
from custom_components.hughes_power_watchdog.models import PowerWatchdogManager


@pytest.fixture()
def manager() -> PowerWatchdogManager:
    hass = MagicMock()
    return PowerWatchdogManager(hass, "AA:BB:CC:DD:EE:FF", "Test Watchdog")


@pytest.fixture()
def button(manager: PowerWatchdogManager) -> WatchdogResetButton:
    return WatchdogResetButton(manager)


# ── Button construction ──────────────────────────────────────────────────────


class TestButtonConstruction:
    """Verify button entity attributes are set correctly."""

    def test_name_includes_device_name(self, button: WatchdogResetButton):
        """Button name includes the device name."""
        assert "Test Watchdog" in button._attr_name

    def test_name_includes_reset(self, button: WatchdogResetButton):
        """Button name indicates it resets energy."""
        assert "Reset" in button._attr_name

    def test_unique_id_format(self, button: WatchdogResetButton):
        """unique_id follows {address}_reset_energy pattern."""
        assert button._attr_unique_id == "AA:BB:CC:DD:EE:FF_reset_energy"

    def test_icon(self, button: WatchdogResetButton):
        """Button has the counter icon."""
        assert button._attr_icon == "mdi:counter"

    def test_device_class(self, button: WatchdogResetButton):
        """Button has the restart device class."""
        assert button._attr_device_class == "restart"


# ── CMD_RESET_ENERGY payload validation ──────────────────────────────────────


class TestResetEnergyPayload:
    """Verify CMD_RESET_ENERGY is a valid framed packet."""

    def test_decodes_to_bytes(self):
        """CMD_RESET_ENERGY is valid hex."""
        payload = bytes.fromhex(CMD_RESET_ENERGY)
        assert len(payload) > 0

    def test_starts_with_identifier(self):
        """Payload starts with the packet identifier."""
        payload = bytes.fromhex(CMD_RESET_ENERGY)
        ident = struct.unpack(">I", payload[:4])[0]
        assert ident == PACKET_IDENTIFIER

    def test_ends_with_tail(self):
        """Payload ends with the packet tail."""
        payload = bytes.fromhex(CMD_RESET_ENERGY)
        tail = struct.unpack(">H", payload[-2:])[0]
        assert tail == PACKET_TAIL

    def test_data_len_matches_body(self):
        """The dataLen field matches the actual body length."""
        payload = bytes.fromhex(CMD_RESET_ENERGY)
        data_len = struct.unpack(">H", payload[7:9])[0]
        expected_body_len = len(payload) - HEADER_SIZE - TAIL_SIZE
        assert data_len == expected_body_len

    def test_total_length_consistent(self):
        """Total length == HEADER_SIZE + dataLen + TAIL_SIZE."""
        payload = bytes.fromhex(CMD_RESET_ENERGY)
        data_len = struct.unpack(">H", payload[7:9])[0]
        assert len(payload) == HEADER_SIZE + data_len + TAIL_SIZE


# ── async_press behaviour ────────────────────────────────────────────────────


class TestAsyncPress:
    """Verify async_press sends the correct payload."""

    @pytest.mark.asyncio
    async def test_sends_payload_when_connected(
        self, manager: PowerWatchdogManager, button: WatchdogResetButton
    ):
        """async_press writes CMD_RESET_ENERGY to the characteristic."""
        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.write_gatt_char = AsyncMock()
        manager.client = mock_client

        await button.async_press()

        mock_client.write_gatt_char.assert_called_once_with(
            CHARACTERISTIC_UUID,
            bytes.fromhex(CMD_RESET_ENERGY),
            response=True,
        )

    @pytest.mark.asyncio
    async def test_no_write_when_disconnected(
        self, manager: PowerWatchdogManager, button: WatchdogResetButton
    ):
        """async_press does nothing when the client is disconnected."""
        mock_client = MagicMock()
        mock_client.is_connected = False
        mock_client.write_gatt_char = AsyncMock()
        manager.client = mock_client

        await button.async_press()

        mock_client.write_gatt_char.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_write_when_no_client(
        self, manager: PowerWatchdogManager, button: WatchdogResetButton
    ):
        """async_press does nothing when there is no BLE client."""
        manager.client = None

        await button.async_press()
        # Should not raise
