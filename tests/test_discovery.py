"""Tests for BLE device discovery matching.

Verifies that DEVICE_NAME_PREFIXES correctly matches all known Gen 1 and
Gen 2 Power Watchdog advertisement names, and rejects unrelated devices.
"""

from __future__ import annotations

import pytest

from custom_components.hughes_power_watchdog.const import (
    DEVICE_NAME_PREFIXES,
    GEN1_PREFIX,
    GEN2_PREFIX,
)


def _matches(name: str) -> bool:
    """Return True if *name* would be matched by the discovery logic."""
    return bool(name) and any(name.startswith(p) for p in DEVICE_NAME_PREFIXES)


# ── Gen 2 devices (WD_*) ────────────────────────────────────────────────────


class TestGen2Discovery:
    """Gen 2 devices advertise as WD_{type}_{serialhex}."""

    @pytest.mark.parametrize(
        "name",
        [
            "WD_V5_aabbccddeeff",
            "WD_V6_aabbccddeeff",
            "WD_V7_aabbccddeeff",
            "WD_V8_aabbccddeeff",
            "WD_V9_aabbccddeeff",
            "WD_E5_aabbccddeeff",
            "WD_E6_aabbccddeeff",
            "WD_E7_26ec4ae469a5",
            "WD_E8_aabbccddeeff",
            "WD_E9_aabbccddeeff",
        ],
    )
    def test_gen2_matched(self, name: str):
        """All known Gen 2 type codes are matched."""
        assert _matches(name) is True

    def test_gen2_prefix_constant(self):
        """GEN2_PREFIX is WD_ and is in DEVICE_NAME_PREFIXES."""
        assert GEN2_PREFIX == "WD_"
        assert GEN2_PREFIX in DEVICE_NAME_PREFIXES


# ── Gen 1 devices (PM*) ─────────────────────────────────────────────────────


class TestGen1Discovery:
    """Gen 1 devices advertise as PM{S|D}... (19-char name)."""

    @pytest.mark.parametrize(
        "name",
        [
            "PMS1234567890123456",   # 30A single (19 chars)
            "PMD1234567890123456",   # 50A dual   (19 chars)
            "PMS1234567890123456        ",  # trailing spaces (27 chars)
            "PMD1234567890123456        ",
        ],
    )
    def test_gen1_matched(self, name: str):
        """All known Gen 1 naming patterns are matched."""
        assert _matches(name) is True

    def test_gen1_prefix_constant(self):
        """GEN1_PREFIX is PM and is in DEVICE_NAME_PREFIXES."""
        assert GEN1_PREFIX == "PM"
        assert GEN1_PREFIX in DEVICE_NAME_PREFIXES


# ── Non-matching devices ─────────────────────────────────────────────────────


class TestNonMatching:
    """Devices that should NOT be matched by discovery."""

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "iPhone",
            "SmartPlug_123",
            "WATCHDOG_E7",
            "wd_E7_aabbccddeeff",   # lowercase — different device
            "WD",                    # missing underscore
        ],
    )
    def test_not_matched(self, name: str):
        """Unrelated BLE names are not matched."""
        assert _matches(name) is False

    def test_none_safe(self):
        """Empty string returns False (caller should guard None)."""
        assert _matches("") is False
