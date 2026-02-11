from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN, CMD_RESET_ENERGY, CHARACTERISTIC_UUID

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Power Watchdog button."""
    manager = hass.data[DOMAIN][entry.entry_id]["manager"]
    async_add_entities([WatchdogResetButton(manager)])

class WatchdogResetButton(ButtonEntity):
    """Representation of a Power Watchdog Reset Button."""

    def __init__(self, manager):
        self._manager = manager
        self._attr_name = f"{manager.name} Reset Total Energy"
        self._attr_unique_id = f"{manager.address}_reset_energy"
        self._attr_icon = "mdi:counter"
        self._attr_device_class = "restart"
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, manager.address)},
            name=manager.name,
            manufacturer="Hughes Autoformers",
            model="Power Watchdog Gen 2",
        )

    async def async_press(self) -> None:
        """Handle the button press to reset energy."""
        if self._manager.client and self._manager.client.is_connected:
            payload = bytes.fromhex(CMD_RESET_ENERGY)
            await self._manager.client.write_gatt_char(
                CHARACTERISTIC_UUID, 
                payload, 
                response=True
            )
