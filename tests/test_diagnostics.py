"""Tests for the diagnostics support module.

Covers the shape of the returned diagnostics dict and, importantly, that
the device's BLE MAC address is redacted before it would be attached to a
GitHub issue.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from tests.helpers import build_30a_packet
from custom_components.hughes_power_watchdog.const import DOMAIN
from custom_components.hughes_power_watchdog.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.hughes_power_watchdog.models import PowerWatchdogManager


@pytest.fixture()
def manager() -> PowerWatchdogManager:
    hass = MagicMock()
    mgr = PowerWatchdogManager(
        hass, "AA:BB:CC:DD:EE:FF", "Test Watchdog",
        ble_name="WD_V6_aabbccddeeff",
    )
    mgr.client = MagicMock(is_connected=True)
    return mgr


@pytest.fixture()
def entry(manager: PowerWatchdogManager) -> MagicMock:
    mock_entry = MagicMock()
    mock_entry.title = "Test Watchdog"
    mock_entry.version = 1
    mock_entry.data = {
        "address": "AA:BB:CC:DD:EE:FF",
        "device_name": "Test Watchdog",
        "ble_name": "WD_V6_aabbccddeeff",
    }
    mock_entry.entry_id = "test_entry_id"
    return mock_entry


@pytest.fixture()
def hass(manager: PowerWatchdogManager, entry: MagicMock) -> MagicMock:
    mock_hass = MagicMock()
    mock_hass.data = {DOMAIN: {entry.entry_id: {"manager": manager}}}
    return mock_hass


class TestDiagnosticsRedaction:
    """The BLE MAC address must never appear in plain text in diagnostics."""

    def test_address_redacted_in_manager_section(
        self, hass: MagicMock, entry: MagicMock
    ):
        result = asyncio.run(async_get_config_entry_diagnostics(hass, entry))
        assert result["manager"]["address"] == "**REDACTED**"

    def test_address_redacted_in_entry_data(
        self, hass: MagicMock, entry: MagicMock
    ):
        result = asyncio.run(async_get_config_entry_diagnostics(hass, entry))
        assert result["entry"]["data"]["address"] == "**REDACTED**"

    def test_raw_address_not_present_anywhere(
        self, hass: MagicMock, entry: MagicMock
    ):
        """The literal MAC address string must not appear anywhere in the dump."""
        result = asyncio.run(async_get_config_entry_diagnostics(hass, entry))
        assert "AA:BB:CC:DD:EE:FF" not in repr(result)

    def test_non_sensitive_fields_untouched(
        self, hass: MagicMock, entry: MagicMock
    ):
        """Redaction only targets the address — everything else survives."""
        result = asyncio.run(async_get_config_entry_diagnostics(hass, entry))
        assert result["manager"]["ble_name"] == "WD_V6_aabbccddeeff"
        assert result["manager"]["generation"] == 2
        assert result["entry"]["title"] == "Test Watchdog"


class TestDiagnosticsContent:
    """Verify the diagnostics payload reflects live telemetry."""

    def test_no_l2_when_single_line(self, hass: MagicMock, entry: MagicMock):
        result = asyncio.run(async_get_config_entry_diagnostics(hass, entry))
        assert result["raw_data"]["has_l2"] is False
        assert result["raw_data"]["l2"] is None

    def test_l1_reflects_latest_telemetry(
        self, hass: MagicMock, entry: MagicMock, manager: PowerWatchdogManager
    ):
        pkt = build_30a_packet(voltage=121.5, power=203.0)
        manager._protocol.notification_handler(None, bytearray(pkt))

        result = asyncio.run(async_get_config_entry_diagnostics(hass, entry))
        assert result["raw_data"]["l1"]["voltage"] == 121.5
        assert result["raw_data"]["l1"]["power"] == 203.0

    def test_is_connected_reflects_client_state(
        self, hass: MagicMock, entry: MagicMock, manager: PowerWatchdogManager
    ):
        result = asyncio.run(async_get_config_entry_diagnostics(hass, entry))
        assert result["manager"]["is_connected"] is True

        manager.client = None
        result = asyncio.run(async_get_config_entry_diagnostics(hass, entry))
        assert result["manager"]["is_connected"] is False
