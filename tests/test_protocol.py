"""Tests for the Power Watchdog binary protocol parser.

Covers packet framing, reassembly, DLData field parsing, command dispatch,
and edge cases such as fragmentation, bad tails, and buffer overflow.
"""

from __future__ import annotations

import struct

import pytest

from tests.helpers import (
    build_30a_packet,
    build_50a_packet,
    build_dl_data,
    build_packet,
)
from custom_components.hughes_power_watchdog.const import (
    CMD_ALARM,
    CMD_DL_REPORT,
    CMD_ERROR_REPORT,
    DL_DATA_SIZE,
    HEADER_SIZE,
    MAX_BUFFER_SIZE,
    PACKET_IDENTIFIER,
    PACKET_TAIL,
    TAIL_SIZE,
)
from custom_components.hughes_power_watchdog.models import (
    LineData,
    PowerWatchdogManager,
    WatchdogData,
)


# ── Static _parse_dl_data tests ─────────────────────────────────────────────


class TestParseDlData:
    """Tests for PowerWatchdogManager._parse_dl_data (static method)."""

    def test_voltage_scaling(self):
        """Voltage raw int divided by 10 000 → volts."""
        body = build_dl_data(voltage=121.5)
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.voltage == 121.5

    def test_current_scaling(self):
        """Current raw int divided by 10 000 → amps."""
        body = build_dl_data(current=2.03)
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.current == 2.03

    def test_power_scaling(self):
        """Power raw int divided by 10 000 → watts."""
        body = build_dl_data(power=203.0)
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.power == 203.0

    def test_energy_scaling(self):
        """Energy raw int divided by 10 000 → kWh."""
        body = build_dl_data(energy=2645.05)
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.energy == 2645.05

    def test_output_voltage_scaling(self):
        """Output voltage raw int divided by 10 000 → volts."""
        body = build_dl_data(output_voltage=122.0)
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.output_voltage == 122.0

    def test_frequency_scaling(self):
        """Frequency raw int divided by 100 → Hz."""
        body = build_dl_data(frequency=60.0)
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.frequency == 60.0

    def test_error_code(self):
        """Error code passed through as-is."""
        body = build_dl_data(error=3)
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.error_code == 3

    def test_status(self):
        """Status byte passed through as-is."""
        body = build_dl_data(status=2)
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.status == 2

    def test_boost_true(self):
        """Boost flag == 1 → True."""
        body = build_dl_data(boost=True)
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.boost is True

    def test_boost_false(self):
        """Boost flag == 0 → False."""
        body = build_dl_data(boost=False)
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.boost is False

    def test_all_fields_together(self):
        """Verify all fields are parsed correctly in a single block."""
        body = build_dl_data(
            voltage=120.1,
            current=15.5,
            power=1860.0,
            energy=100.0,
            output_voltage=121.0,
            frequency=50.0,
            error=5,
            status=1,
            boost=True,
        )
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.voltage == 120.1
        assert result.current == 15.5
        assert result.power == 1860.0
        assert result.energy == 100.0
        assert result.output_voltage == 121.0
        assert result.frequency == 50.0
        assert result.error_code == 5
        assert result.status == 1
        assert result.boost is True

    def test_offset_into_larger_buffer(self):
        """Parsing with a non-zero offset reads the second DLData block."""
        l1 = build_dl_data(voltage=121.0)
        l2 = build_dl_data(voltage=122.7)
        combined = l1 + l2

        result_l1 = PowerWatchdogManager._parse_dl_data(combined, 0)
        result_l2 = PowerWatchdogManager._parse_dl_data(combined, DL_DATA_SIZE)

        assert result_l1.voltage == 121.0
        assert result_l2.voltage == 122.7

    def test_zero_values(self):
        """All-zero data produces zero values without errors."""
        body = build_dl_data(
            voltage=0.0, current=0.0, power=0.0,
            energy=0.0, output_voltage=0.0, frequency=0.0,
            error=0, status=0,
        )
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.voltage == 0.0
        assert result.current == 0.0
        assert result.power == 0.0
        assert result.frequency == 0.0

    def test_block_size(self):
        """build_dl_data produces exactly DL_DATA_SIZE bytes."""
        body = build_dl_data()
        assert len(body) == DL_DATA_SIZE


# ── Packet framing and reassembly tests ──────────────────────────────────────


class TestPacketReassembly:
    """Tests for the notification handler and packet reassembly buffer."""

    def test_complete_30a_packet(self, manager: PowerWatchdogManager):
        """A single complete 30A packet updates L1 data, has_l2 = False."""
        pkt = build_30a_packet(voltage=121.5, current=2.03, power=203.0)
        manager._notification_handler(None, bytearray(pkt))

        assert manager.data.l1.voltage == 121.5
        assert manager.data.l1.current == 2.03
        assert manager.data.l1.power == 203.0
        assert manager.data.has_l2 is False

    def test_complete_50a_packet(self, manager: PowerWatchdogManager):
        """A single complete 50A packet updates both L1 and L2, has_l2 = True."""
        pkt = build_50a_packet(
            l1_voltage=121.5, l1_current=2.03, l1_power=203.0,
            l2_voltage=122.7, l2_current=0.36, l2_power=7.0,
        )
        manager._notification_handler(None, bytearray(pkt))

        assert manager.data.l1.voltage == 121.5
        assert manager.data.l1.current == 2.03
        assert manager.data.l2.voltage == 122.7
        assert manager.data.l2.current == 0.36
        assert manager.data.has_l2 is True

    def test_fragmented_delivery(self, manager: PowerWatchdogManager):
        """A 50A packet split across three notifications is reassembled."""
        pkt = build_50a_packet(l1_voltage=120.0, l2_voltage=121.0)
        # Simulate MTU ~20 byte fragmentation
        chunk_size = 20
        chunks = [pkt[i : i + chunk_size] for i in range(0, len(pkt), chunk_size)]
        assert len(chunks) >= 3, "packet should fragment into 3+ chunks"

        for chunk in chunks[:-1]:
            manager._notification_handler(None, bytearray(chunk))
            # Data should not be updated yet (incomplete packet)

        # Final chunk completes the packet
        manager._notification_handler(None, bytearray(chunks[-1]))
        assert manager.data.l1.voltage == 120.0
        assert manager.data.l2.voltage == 121.0
        assert manager.data.has_l2 is True

    def test_two_packets_in_one_notification(self, manager: PowerWatchdogManager):
        """Two back-to-back packets in a single notification are both parsed."""
        pkt1 = build_30a_packet(voltage=119.0)
        pkt2 = build_30a_packet(voltage=120.5)
        combined = pkt1 + pkt2

        manager._notification_handler(None, bytearray(combined))

        # The second packet overwrites the first
        assert manager.data.l1.voltage == 120.5

    def test_garbage_before_valid_packet(self, manager: PowerWatchdogManager):
        """Random bytes before a valid packet are skipped."""
        garbage = bytes([0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0x01])
        pkt = build_30a_packet(voltage=122.0)

        manager._notification_handler(None, bytearray(garbage + pkt))

        assert manager.data.l1.voltage == 122.0

    def test_bad_tail_discarded(self, manager: PowerWatchdogManager):
        """A packet with an incorrect tail does not update data."""
        pkt = bytearray(build_30a_packet(voltage=999.0))
        # Corrupt the tail (last 2 bytes)
        pkt[-2] = 0xFF
        pkt[-1] = 0xFF

        manager._notification_handler(None, pkt)

        # Data should remain at defaults (no update)
        assert manager.data.l1.voltage is None

    def test_partial_header_waits(self, manager: PowerWatchdogManager):
        """An incomplete header does not crash; data waits in the buffer."""
        pkt = build_30a_packet(voltage=121.0)
        # Send only the first 5 bytes (less than HEADER_SIZE=9)
        manager._notification_handler(None, bytearray(pkt[:5]))

        assert manager.data.l1.voltage is None
        assert len(manager._rx_buffer) == 5

        # Send the rest
        manager._notification_handler(None, bytearray(pkt[5:]))
        assert manager.data.l1.voltage == 121.0
        assert len(manager._rx_buffer) == 0

    def test_buffer_overflow_protection(self, manager: PowerWatchdogManager):
        """Buffer is cleared when it exceeds MAX_BUFFER_SIZE."""
        manager._rx_buffer = bytearray(MAX_BUFFER_SIZE + 1)
        # Sending any additional data triggers the overflow check
        manager._notification_handler(None, bytearray(b"\x00"))

        assert len(manager._rx_buffer) == 0

    def test_buffer_cleared_after_complete_packet(self, manager: PowerWatchdogManager):
        """Buffer is empty after a complete packet is consumed."""
        pkt = build_30a_packet()
        manager._notification_handler(None, bytearray(pkt))

        assert len(manager._rx_buffer) == 0


# ── Command dispatch tests ───────────────────────────────────────────────────


class TestCommandDispatch:
    """Tests that only DLReport (cmd 1) updates sensor data."""

    def test_error_report_ignored(self, manager: PowerWatchdogManager):
        """ErrorReport (cmd 2) does not update power data."""
        # First, set some valid data
        valid_pkt = build_30a_packet(voltage=121.5)
        manager._notification_handler(None, bytearray(valid_pkt))
        assert manager.data.l1.voltage == 121.5

        # Now send an ErrorReport — data should not change
        error_body = bytes(16)  # 16-byte error record
        error_pkt = build_packet(CMD_ERROR_REPORT, error_body)
        manager._notification_handler(None, bytearray(error_pkt))

        assert manager.data.l1.voltage == 121.5  # unchanged

    def test_alarm_ignored(self, manager: PowerWatchdogManager):
        """Alarm (cmd 14) does not update power data."""
        valid_pkt = build_30a_packet(voltage=121.5)
        manager._notification_handler(None, bytearray(valid_pkt))

        alarm_pkt = build_packet(CMD_ALARM, b"")
        manager._notification_handler(None, bytearray(alarm_pkt))

        assert manager.data.l1.voltage == 121.5  # unchanged

    def test_unknown_cmd_ignored(self, manager: PowerWatchdogManager):
        """Unknown command IDs do not update power data."""
        valid_pkt = build_30a_packet(voltage=121.5)
        manager._notification_handler(None, bytearray(valid_pkt))

        unknown_pkt = build_packet(99, b"\x01\x02\x03")
        manager._notification_handler(None, bytearray(unknown_pkt))

        assert manager.data.l1.voltage == 121.5  # unchanged

    def test_error_report_between_dl_reports(self, manager: PowerWatchdogManager):
        """An ErrorReport between two DLReports doesn't corrupt data.

        This is the exact scenario that caused garbage readings in the
        old fixed-offset parser.
        """
        pkt1 = build_30a_packet(voltage=121.0)
        error_pkt = build_packet(CMD_ERROR_REPORT, bytes(32))
        pkt2 = build_30a_packet(voltage=122.0)

        manager._notification_handler(None, bytearray(pkt1 + error_pkt + pkt2))

        # Final value should be from pkt2, not corrupted by error_pkt
        assert manager.data.l1.voltage == 122.0


# ── DLReport body length tests ───────────────────────────────────────────────


class TestDlReportBodyLength:
    """Tests for handling different DLReport body lengths."""

    def test_34_byte_body_is_30a(self, manager: PowerWatchdogManager):
        """34-byte body → single line, has_l2 = False."""
        body = build_dl_data(voltage=121.0)
        assert len(body) == 34

        pkt = build_packet(CMD_DL_REPORT, body)
        manager._notification_handler(None, bytearray(pkt))

        assert manager.data.has_l2 is False
        assert manager.data.l1.voltage == 121.0

    def test_68_byte_body_is_50a(self, manager: PowerWatchdogManager):
        """68-byte body → dual line, has_l2 = True."""
        l1 = build_dl_data(voltage=121.0)
        l2 = build_dl_data(voltage=122.7)
        body = l1 + l2
        assert len(body) == 68

        pkt = build_packet(CMD_DL_REPORT, body)
        manager._notification_handler(None, bytearray(pkt))

        assert manager.data.has_l2 is True
        assert manager.data.l1.voltage == 121.0
        assert manager.data.l2.voltage == 122.7

    def test_unexpected_body_length_ignored(self, manager: PowerWatchdogManager):
        """A DLReport with an unexpected body length does not update data."""
        body = bytes(50)  # neither 34 nor 68
        pkt = build_packet(CMD_DL_REPORT, body)
        manager._notification_handler(None, bytearray(pkt))

        assert manager.data.l1.voltage is None


# ── Packet structure validation ──────────────────────────────────────────────


class TestPacketStructure:
    """Verify the packet builder produces correct framing bytes."""

    def test_identifier(self):
        """First 4 bytes are the packet identifier."""
        pkt = build_30a_packet()
        ident = struct.unpack(">I", pkt[:4])[0]
        assert ident == PACKET_IDENTIFIER

    def test_tail(self):
        """Last 2 bytes are the packet tail."""
        pkt = build_30a_packet()
        tail = struct.unpack(">H", pkt[-2:])[0]
        assert tail == PACKET_TAIL

    def test_cmd_byte(self):
        """Byte 6 contains the command ID."""
        pkt = build_30a_packet()
        assert pkt[6] == CMD_DL_REPORT

    def test_data_len_30a(self):
        """Bytes 7-8 encode the body length (34 for 30A)."""
        pkt = build_30a_packet()
        data_len = struct.unpack(">H", pkt[7:9])[0]
        assert data_len == DL_DATA_SIZE

    def test_data_len_50a(self):
        """Bytes 7-8 encode the body length (68 for 50A)."""
        pkt = build_50a_packet()
        data_len = struct.unpack(">H", pkt[7:9])[0]
        assert data_len == DL_DATA_SIZE * 2

    def test_30a_total_length(self):
        """A 30A DLReport packet is 9 + 34 + 2 = 45 bytes."""
        pkt = build_30a_packet()
        assert len(pkt) == HEADER_SIZE + DL_DATA_SIZE + TAIL_SIZE

    def test_50a_total_length(self):
        """A 50A DLReport packet is 9 + 68 + 2 = 79 bytes."""
        pkt = build_50a_packet()
        assert len(pkt) == HEADER_SIZE + DL_DATA_SIZE * 2 + TAIL_SIZE


# ── Sensor update callback tests ─────────────────────────────────────────────


class TestSensorUpdateCallback:
    """Verify that registered sensors are notified on data update."""

    def test_sensors_notified_on_dl_report(self, manager: PowerWatchdogManager):
        """All registered sensors get async_write_ha_state called."""
        from unittest.mock import MagicMock

        sensor1 = MagicMock()
        sensor2 = MagicMock()
        manager.register_sensor(sensor1)
        manager.register_sensor(sensor2)

        pkt = build_30a_packet()
        manager._notification_handler(None, bytearray(pkt))

        sensor1.async_write_ha_state.assert_called_once()
        sensor2.async_write_ha_state.assert_called_once()

    def test_sensors_not_notified_on_error_report(
        self, manager: PowerWatchdogManager
    ):
        """Sensors are NOT notified for ErrorReport packets."""
        from unittest.mock import MagicMock

        sensor = MagicMock()
        manager.register_sensor(sensor)

        error_pkt = build_packet(CMD_ERROR_REPORT, bytes(16))
        manager._notification_handler(None, bytearray(error_pkt))

        sensor.async_write_ha_state.assert_not_called()


# ── Signed integer / edge-value tests ────────────────────────────────────────


class TestSignedValues:
    """The protocol uses big-endian signed int32.  Verify negative values parse."""

    def test_negative_current(self):
        """Negative current (e.g., reversed CT clamp) parses correctly."""
        body = build_dl_data(current=-1.5)
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.current == -1.5

    def test_negative_power(self):
        """Negative power (e.g., reverse energy flow) parses correctly."""
        body = build_dl_data(power=-500.0)
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.power == -500.0

    def test_large_energy_value(self):
        """Large cumulative energy value within int32 range."""
        body = build_dl_data(energy=21000.0)  # 210 000 000 raw — fits in int32
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.energy == 21000.0

    def test_high_voltage(self):
        """Voltage near 250V (high end of split-phase)."""
        body = build_dl_data(voltage=248.3)
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.voltage == 248.3

    def test_50hz_frequency(self):
        """50 Hz frequency (international grids)."""
        body = build_dl_data(frequency=50.0)
        result = PowerWatchdogManager._parse_dl_data(body, 0)
        assert result.frequency == 50.0


# ── Invalid dataLen guard ────────────────────────────────────────────────────


class TestInvalidDataLen:
    """Verify the dataLen > MAX_BUFFER_SIZE guard in _try_parse_packet."""

    def test_huge_datalen_skips_identifier(self, manager: PowerWatchdogManager):
        """A packet claiming dataLen > MAX_BUFFER_SIZE skips the identifier."""
        # Build a header with an absurdly large dataLen
        header = struct.pack(">I", PACKET_IDENTIFIER)
        header += bytes([1, 0, CMD_DL_REPORT])
        header += struct.pack(">H", MAX_BUFFER_SIZE + 100)  # way too large

        # Append a valid 30A packet right after the bad header
        good_pkt = build_30a_packet(voltage=121.0)
        manager._notification_handler(None, bytearray(header + good_pkt))

        # The bad header should be skipped, and the good packet parsed
        assert manager.data.l1.voltage == 121.0


# ── Protocol constant sanity checks ──────────────────────────────────────────


class TestProtocolConstants:
    """Verify key protocol constants have correct values."""

    def test_header_size(self):
        """HEADER_SIZE = 4 (ident) + 1 (ver) + 1 (msg) + 1 (cmd) + 2 (len) = 9."""
        assert HEADER_SIZE == 9

    def test_tail_size(self):
        """TAIL_SIZE = 2 bytes."""
        assert TAIL_SIZE == 2

    def test_dl_data_size(self):
        """DL_DATA_SIZE = 34 bytes per line."""
        assert DL_DATA_SIZE == 34

    def test_packet_identifier(self):
        """PACKET_IDENTIFIER = 0x24797740."""
        assert PACKET_IDENTIFIER == 0x24797740

    def test_packet_tail(self):
        """PACKET_TAIL = 0x7121."""
        assert PACKET_TAIL == 0x7121

    def test_cmd_dl_report(self):
        """CMD_DL_REPORT = 1."""
        assert CMD_DL_REPORT == 1

    def test_cmd_error_report(self):
        """CMD_ERROR_REPORT = 2."""
        assert CMD_ERROR_REPORT == 2

    def test_cmd_alarm(self):
        """CMD_ALARM = 14."""
        assert CMD_ALARM == 14


# ── Handshake payload validation ─────────────────────────────────────────────


class TestHandshakePayload:
    """Verify the handshake payload is correct."""

    def test_handshake_is_ascii(self):
        """HANDSHAKE_PAYLOAD decodes to the expected ASCII string."""
        from custom_components.hughes_power_watchdog.const import HANDSHAKE_PAYLOAD

        assert HANDSHAKE_PAYLOAD == b"!%!%,protocol,open,"

    def test_handshake_length(self):
        """HANDSHAKE_PAYLOAD is 19 bytes."""
        from custom_components.hughes_power_watchdog.const import HANDSHAKE_PAYLOAD

        assert len(HANDSHAKE_PAYLOAD) == 19
