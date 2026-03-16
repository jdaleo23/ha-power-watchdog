"""Shared device info helper for the Hughes Power Watchdog integration."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


def build_device_info(manager) -> DeviceInfo:  # noqa: ANN001
    """Return a consistent DeviceInfo for all Power Watchdog entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, manager.address)},
        name=manager.name,
        manufacturer="Hughes Autoformers",
        model="Power Watchdog",
    )
