"""Packet builder helpers for Power Watchdog protocol tests."""

from __future__ import annotations

import struct

from custom_components.hughes_power_watchdog.const import (
    CMD_DL_REPORT,
    PACKET_IDENTIFIER,
    PACKET_TAIL,
)


def build_dl_data(
    voltage: float = 121.5,
    current: float = 2.03,
    power: float = 203.0,
    energy: float = 2645.05,
    output_voltage: float = 122.0,
    frequency: float = 60.0,
    error: int = 0,
    status: int = 1,
    boost: bool = False,
) -> bytes:
    """Build a 34-byte DLData block with the given values."""
    return (
        struct.pack(">i", int(voltage * 10_000))
        + struct.pack(">i", int(current * 10_000))
        + struct.pack(">i", int(power * 10_000))
        + struct.pack(">i", int(energy * 10_000))
        + struct.pack(">i", 0)  # temp1 (reserved)
        + struct.pack(">i", int(output_voltage * 10_000))
        + bytes([5, 0, 1 if boost else 0, 25])  # backlight, neutral, boost, temp
        + struct.pack(">i", int(frequency * 100))
        + bytes([error, status])
    )


def build_packet(cmd: int, body: bytes) -> bytes:
    """Build a complete framed packet with identifier, header, body, and tail."""
    header = struct.pack(">I", PACKET_IDENTIFIER)
    header += bytes([1, 0, cmd])  # version=1, msgId=0, cmd
    header += struct.pack(">H", len(body))
    tail = struct.pack(">H", PACKET_TAIL)
    return header + body + tail


def build_30a_packet(
    voltage: float = 121.5,
    current: float = 2.03,
    power: float = 203.0,
    energy: float = 2645.05,
    output_voltage: float = 122.0,
    frequency: float = 60.0,
    error: int = 0,
    status: int = 1,
) -> bytes:
    """Build a complete 30A single-line DLReport packet."""
    body = build_dl_data(
        voltage=voltage, current=current, power=power,
        energy=energy, output_voltage=output_voltage,
        frequency=frequency, error=error, status=status,
    )
    return build_packet(CMD_DL_REPORT, body)


def build_50a_packet(
    l1_voltage: float = 121.5,
    l1_current: float = 2.03,
    l1_power: float = 203.0,
    l1_energy: float = 2645.05,
    l2_voltage: float = 122.7,
    l2_current: float = 0.36,
    l2_power: float = 7.0,
    l2_energy: float = 500.25,
    frequency: float = 60.0,
) -> bytes:
    """Build a complete 50A dual-line DLReport packet (L1 + L2)."""
    l1 = build_dl_data(
        voltage=l1_voltage, current=l1_current, power=l1_power,
        energy=l1_energy, frequency=frequency,
    )
    l2 = build_dl_data(
        voltage=l2_voltage, current=l2_current, power=l2_power,
        energy=l2_energy, frequency=frequency,
    )
    return build_packet(CMD_DL_REPORT, l1 + l2)
