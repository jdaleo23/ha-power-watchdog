"""Diagnostics support for Hughes Power Watchdog."""
from __future__ import annotations

from typing import Any
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .const import CONF_BLE_NAME, DOMAIN

# The raw BLE advertisement name embeds the same MAC address as CONF_ADDRESS,
# just without separators (e.g. "WD_V6_aabbccddeeff" for "AA:BB:CC:DD:EE:FF"),
# so it needs to be redacted too rather than just the address field.
TO_REDACT = {CONF_ADDRESS, CONF_BLE_NAME}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    manager = hass.data[DOMAIN][entry.entry_id]["manager"]

    # This dictionary is what will be inside the downloaded file
    diagnostics = {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "data": dict(entry.data),
        },
        "manager": {
            "address": manager.address,
            "ble_name": manager.ble_name,
            "generation": manager.generation,
            "is_connected": manager.client.is_connected if manager.client else False,
        },
        "raw_data": {
            "has_l2": manager.data.has_l2,
            "l1": {
                "voltage": manager.data.l1.voltage,
                "current": manager.data.l1.current,
                "power": manager.data.l1.power,
                "energy": manager.data.l1.energy,
                "output_voltage": manager.data.l1.output_voltage,
                "boost_active": manager.data.l1.boost,
                "error_code": manager.data.l1.error_code,
            },
            "l2": {
                "voltage": manager.data.l2.voltage,
                "current": manager.data.l2.current,
                "power": manager.data.l2.power,
                "energy": manager.data.l2.energy,
                "output_voltage": manager.data.l2.output_voltage,
                "boost_active": manager.data.l2.boost,
                "error_code": manager.data.l2.error_code,
            } if manager.data.has_l2 else None,
        }
    }

    return async_redact_data(diagnostics, TO_REDACT)
