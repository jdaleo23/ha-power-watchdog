"""Tests for the Gen1 Power Watchdog raw Modbus-style protocol parser.

Covers 20-byte chunk reassembly, 40-byte telemetry parsing with unsigned
uint32 values, hardware version detection from BLE names, and dual-line
marker logic for v1 vs v2/v3 devices.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.helpers import build_gen1_chunks
from custom_components.hughes_power_watchdog.const import (
    GEN1_CHUNK_SIZE,
    GEN1_HEADER,
    GEN1_MERGED_SIZE,
)
from custom_components.hughes_power_watchdog.models import (
    PowerWatchdogManager,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def gen1_v2_single() -> PowerWatchdogManager:
    """Gen1 v2 single-line (PMS...E3...)."""
    hass = MagicMock()
    return PowerWatchdogManager(
        hass, "AA:BB:CC:DD:EE:FF", "Test Gen1",
        ble_name="PMS123456789012E3xx",
    )


@pytest.fixture()
def gen1_v1_dual() -> PowerWatchdogManager:
    """Gen1 v1 dual-line (PMD...E2...)."""
    hass = MagicMock()
    return PowerWatchdogManager(
        hass, "AA:BB:CC:DD:EE:FF", "Test Gen1",
        ble_name="PMD123456789012E2xx",
    )


@pytest.fixture()
def gen1_v2_dual() -> PowerWatchdogManager:
    """Gen1 v2 dual-line (PMD...E3...)."""
    hass = MagicMock()
    return PowerWatchdogManager(
        hass, "AA:BB:CC:DD:EE:FF", "Test Gen1",
        ble_name="PMD123456789012E3xx",
    )


def _send_chunks(mgr: PowerWatchdogManager, first: bytes, second: bytes) -> None:
    """Feed a pair of Gen1 chunks through the protocol handler."""
    mgr._protocol.notification_handler(None, bytearray(first))
    mgr._protocol.notification_handler(None, bytearray(second))


# ── Protocol selection ───────────────────────────────────────────────────────


class TestProtocolSelection:
    """Verify that Gen1 BLE names produce a Gen1 protocol handler."""

    def test_gen1_protocol_selected(self, gen1_v2_single: PowerWatchdogManager):
        assert gen1_v2_single.generation == 1

    def test_gen2_default(self):
        hass = MagicMock()
        mgr = PowerWatchdogManager(hass, "XX", "Test", ble_name="WD_E7_aabb")
        assert mgr.generation == 2

    def test_empty_ble_name_defaults_gen2(self):
        hass = MagicMock()
        mgr = PowerWatchdogManager(hass, "XX", "Test")
        assert mgr.generation == 2


# ── Chunk reassembly ────────────────────────────────────────────────────────


class TestChunkReassembly:
    """Verify 20+20 byte chunk pairing into 40-byte frames."""

    def test_basic_reassembly(self, gen1_v2_single: PowerWatchdogManager):
        """Two consecutive chunks produce valid telemetry."""
        first, second = build_gen1_chunks(voltage=121.5, current=2.03)
        _send_chunks(gen1_v2_single, first, second)

        assert gen1_v2_single.data.l1.voltage == 121.5
        assert gen1_v2_single.data.l1.current == 2.03

    def test_non_20_byte_ignored(self, gen1_v2_single: PowerWatchdogManager):
        """Notifications that are not exactly 20 bytes are discarded."""
        gen1_v2_single._protocol.notification_handler(
            None, bytearray(b"\x01\x02\x03"),
        )
        assert gen1_v2_single.data.l1.voltage is None

    def test_orphan_second_chunk_ignored(self, gen1_v2_single: PowerWatchdogManager):
        """A second chunk without a preceding first chunk is discarded."""
        _, second = build_gen1_chunks(voltage=999.0)
        gen1_v2_single._protocol.notification_handler(None, bytearray(second))
        assert gen1_v2_single.data.l1.voltage is None

    def test_duplicate_header_replaces(self, gen1_v2_single: PowerWatchdogManager):
        """A new first-chunk header replaces any buffered first chunk."""
        first_old, _ = build_gen1_chunks(voltage=100.0)
        first_new, second_new = build_gen1_chunks(voltage=200.0)

        gen1_v2_single._protocol.notification_handler(
            None, bytearray(first_old),
        )
        _send_chunks(gen1_v2_single, first_new, second_new)

        assert gen1_v2_single.data.l1.voltage == 200.0


# ── Field parsing (unsigned uint32) ──────────────────────────────────────────


class TestFieldParsing:
    """Verify telemetry field extraction and scaling."""

    def test_voltage(self, gen1_v2_single: PowerWatchdogManager):
        first, second = build_gen1_chunks(voltage=121.5)
        _send_chunks(gen1_v2_single, first, second)
        assert gen1_v2_single.data.l1.voltage == 121.5

    def test_current(self, gen1_v2_single: PowerWatchdogManager):
        first, second = build_gen1_chunks(current=15.03)
        _send_chunks(gen1_v2_single, first, second)
        assert gen1_v2_single.data.l1.current == 15.03

    def test_power(self, gen1_v2_single: PowerWatchdogManager):
        first, second = build_gen1_chunks(power=1860.0)
        _send_chunks(gen1_v2_single, first, second)
        assert gen1_v2_single.data.l1.power == 1860.0

    def test_energy(self, gen1_v2_single: PowerWatchdogManager):
        first, second = build_gen1_chunks(energy=2645.05)
        _send_chunks(gen1_v2_single, first, second)
        assert gen1_v2_single.data.l1.energy == 2645.05

    def test_frequency(self, gen1_v2_single: PowerWatchdogManager):
        first, second = build_gen1_chunks(frequency=60.0)
        _send_chunks(gen1_v2_single, first, second)
        assert gen1_v2_single.data.l1.frequency == 60.0

    def test_error_code(self, gen1_v2_single: PowerWatchdogManager):
        first, second = build_gen1_chunks(error=5)
        _send_chunks(gen1_v2_single, first, second)
        assert gen1_v2_single.data.l1.error_code == 5

    def test_gen1_has_no_output_voltage(self, gen1_v2_single: PowerWatchdogManager):
        """Gen1 protocol does not produce output_voltage."""
        first, second = build_gen1_chunks()
        _send_chunks(gen1_v2_single, first, second)
        assert gen1_v2_single.data.l1.output_voltage is None

    def test_gen1_has_no_boost(self, gen1_v2_single: PowerWatchdogManager):
        """Gen1 protocol does not produce boost flag."""
        first, second = build_gen1_chunks()
        _send_chunks(gen1_v2_single, first, second)
        assert gen1_v2_single.data.l1.boost is None


# ── Dual-line detection: v2/v3 ──────────────────────────────────────────────


class TestDualLineV2V3:
    """v2/v3 devices use (1,1,1) markers for L2."""

    def test_l1_frame(self, gen1_v2_dual: PowerWatchdogManager):
        """Non-(1,1,1) markers → L1."""
        first, second = build_gen1_chunks(voltage=121.0, markers=(0, 0, 0))
        _send_chunks(gen1_v2_dual, first, second)
        assert gen1_v2_dual.data.l1.voltage == 121.0

    def test_l2_frame(self, gen1_v2_dual: PowerWatchdogManager):
        """(1,1,1) markers → L2, sets has_l2."""
        first, second = build_gen1_chunks(voltage=122.7, markers=(1, 1, 1))
        _send_chunks(gen1_v2_dual, first, second)
        assert gen1_v2_dual.data.l2.voltage == 122.7
        assert gen1_v2_dual.data.has_l2 is True

    def test_alternating_frames(self, gen1_v2_dual: PowerWatchdogManager):
        """Alternating L1/L2 frames update the correct lines."""
        l1_first, l1_second = build_gen1_chunks(
            voltage=121.0, markers=(0, 0, 0),
        )
        l2_first, l2_second = build_gen1_chunks(
            voltage=122.7, markers=(1, 1, 1),
        )

        _send_chunks(gen1_v2_dual, l1_first, l1_second)
        _send_chunks(gen1_v2_dual, l2_first, l2_second)

        assert gen1_v2_dual.data.l1.voltage == 121.0
        assert gen1_v2_dual.data.l2.voltage == 122.7
        assert gen1_v2_dual.data.has_l2 is True


# ── Dual-line detection: v1 ─────────────────────────────────────────────────


class TestDualLineV1:
    """v1 devices use non-zero markers to confirm dual-line, (0,0,0) for L2."""

    def test_first_zero_markers_go_to_l1(self, gen1_v1_dual: PowerWatchdogManager):
        """Before dual-line confirmed, (0,0,0) is assigned to L1.

        However, v1 dual-line pre-seeded from BLE name sets has_l2=True,
        so (0,0,0) goes to L2 immediately.
        """
        assert gen1_v1_dual.data.has_l2 is True
        first, second = build_gen1_chunks(voltage=120.0, markers=(0, 0, 0))
        _send_chunks(gen1_v1_dual, first, second)
        assert gen1_v1_dual.data.l2.voltage == 120.0

    def test_nonzero_markers_confirm_dual(self, gen1_v1_dual: PowerWatchdogManager):
        """Non-zero markers → L1 and confirm dual-line."""
        first, second = build_gen1_chunks(
            voltage=121.0, markers=(3, 5, 7),
        )
        _send_chunks(gen1_v1_dual, first, second)
        assert gen1_v1_dual.data.l1.voltage == 121.0
        assert gen1_v1_dual.data.has_l2 is True

    def test_v1_no_preseed_single_line(self):
        """A v1 single-line device keeps (0,0,0) as L1."""
        hass = MagicMock()
        mgr = PowerWatchdogManager(
            hass, "XX", "Test",
            ble_name="PMS123456789012E2xx",
        )
        assert mgr.data.has_l2 is False

        first, second = build_gen1_chunks(voltage=120.0, markers=(0, 0, 0))
        _send_chunks(mgr, first, second)
        assert mgr.data.l1.voltage == 120.0
        assert mgr.data.has_l2 is False


# ── Hardware version detection from BLE name ─────────────────────────────────


class TestHardwareVersionDetection:
    """Verify _init_from_name correctly identifies hardware versions."""

    def test_e2_is_v1(self):
        hass = MagicMock()
        mgr = PowerWatchdogManager(
            hass, "XX", "Test",
            ble_name="PMS123456789012E2xx",
        )
        assert mgr.generation == 1
        assert mgr._protocol._is_v2v3 is False

    def test_e3_is_v2(self):
        hass = MagicMock()
        mgr = PowerWatchdogManager(
            hass, "XX", "Test",
            ble_name="PMS123456789012E3xx",
        )
        assert mgr._protocol._is_v2v3 is True

    def test_e4_is_v3(self):
        hass = MagicMock()
        mgr = PowerWatchdogManager(
            hass, "XX", "Test",
            ble_name="PMS123456789012E4xx",
        )
        assert mgr._protocol._is_v2v3 is True

    def test_short_name_no_crash(self):
        """A name too short for version extraction doesn't crash."""
        hass = MagicMock()
        mgr = PowerWatchdogManager(hass, "XX", "Test", ble_name="PMS")
        assert mgr.generation == 1


# ── Sensor notification ──────────────────────────────────────────────────────


class TestSensorNotification:
    """Verify sensors are notified on each Gen1 telemetry frame."""

    def test_sensors_notified(self, gen1_v2_single: PowerWatchdogManager):
        sensor = MagicMock()
        gen1_v2_single.register_sensor(sensor)

        first, second = build_gen1_chunks()
        _send_chunks(gen1_v2_single, first, second)

        sensor.async_write_ha_state.assert_called_once()


# ── Gen1 protocol constant sanity checks ─────────────────────────────────────


class TestGen1Constants:
    """Verify Gen1-specific protocol constants."""

    def test_chunk_size(self):
        assert GEN1_CHUNK_SIZE == 20

    def test_merged_size(self):
        assert GEN1_MERGED_SIZE == 40

    def test_header(self):
        assert GEN1_HEADER == bytes([0x01, 0x03, 0x20])
