"""Diagnostics support for Hughes Power Watchdog."""
from __future__ import annotations

from typing import Any
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    manager = hass.data[DOMAIN][entry.entry_id]["manager"]
    
    # This dictionary is what will be inside the downloaded file
    return {
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
