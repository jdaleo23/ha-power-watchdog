"""Button platform for the Hughes Power Watchdog integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CHARACTERISTIC_UUID, CMD_RESET_ENERGY, DOMAIN
from .device_info import build_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Power Watchdog button."""
    manager = hass.data[DOMAIN][entry.entry_id]["manager"]
    async_add_entities([WatchdogResetButton(manager)])


class WatchdogResetButton(ButtonEntity):
    """Button that sends the energy-counter reset command.

    Only available on Gen2 devices — Gen1 has no documented reset command.
    """

    def __init__(self, manager) -> None:  # noqa: ANN001
        self._manager = manager
        self._attr_name = f"{manager.name} Reset Total Energy"
        self._attr_unique_id = f"{manager.address}_reset_energy"
        self._attr_icon = "mdi:counter"
        self._attr_device_class = "restart"
        self._attr_device_info = build_device_info(manager)

    @property
    def available(self) -> bool:
        """Unavailable on Gen1 devices or when disconnected."""
        if self._manager.generation == 1:
            return False
        return bool(self._manager.client and self._manager.client.is_connected)

    async def async_press(self) -> None:
        """Send the energy reset command to the device."""
        if self._manager.client and self._manager.client.is_connected:
            payload = bytes.fromhex(CMD_RESET_ENERGY)
            await self._manager.client.write_gatt_char(
                CHARACTERISTIC_UUID,
                payload,
                response=True,
            )
