import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS

from .const import DOMAIN, CONF_DEVICE_NAME

_LOGGER = logging.getLogger(__name__)

class PowerWatchdogConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Power Watchdog."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            # Create the integration entry
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_DEVICE_NAME], data=user_input)

        # Look for devices
        current_addresses = self._async_current_ids()
        discovered_devices = {}
        
        # Scan for devices starting with "WD_V6" (from manifest matching)
        for service_info in async_discovered_service_info(self.hass):
            address = service_info.address
            if address in current_addresses or address in discovered_devices:
                continue
            
            # Check if name matches our pattern
            if service_info.name.startswith("WD_V6"):
                discovered_devices[address] = f"{service_info.name} ({address})"

        if not discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                {
                    config_entries.vol.Required(CONF_ADDRESS): config_entries.vol.In(discovered_devices),
                    config_entries.vol.Required(CONF_DEVICE_NAME, default="Hughes Power Watchdog"): str,
                },
                user_input,
            ),
            errors=errors,
        )
    
    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        """Handle a discovered Bluetooth device."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        
        # Update the name to be friendly
        name = discovery_info.name
        return await self.async_step_user({
             CONF_ADDRESS: discovery_info.address, 
             CONF_DEVICE_NAME: name

        })
