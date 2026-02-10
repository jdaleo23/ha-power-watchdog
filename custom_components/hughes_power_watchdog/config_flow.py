import logging
import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

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
            
            return self.async_create_entry(
                title=user_input[CONF_DEVICE_NAME], 
                data=user_input
            )

        # Look for devices
        current_addresses = self._async_current_ids()
        discovered_devices = {}
        
        # Scan for devices starting with "WD_V6"
        for service_info in async_discovered_service_info(self.hass):
            address = service_info.address
            name = service_info.name
            
            if address in current_addresses or address in discovered_devices:
                continue
            
            # Safe check for name in case advertisement is empty
            if name and name.startswith("WD_V6"):
                discovered_devices[address] = f"{name} ({address})"

        if not discovered_devices:
            return self.async_abort(reason="no_devices_found")

        # Create dropdown options for the selector
        options = [
            {"value": addr, "label": label}
            for addr, label in discovered_devices.items()
        ]

        # Use SelectSelector for a polished dropdown UI
        data_schema = vol.Schema({
            vol.Required(CONF_ADDRESS): SelectSelector(
                SelectSelectorConfig(
                    options=options,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(CONF_DEVICE_NAME, default="Hughes Power Watchdog"): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                data_schema, 
                user_input
            ),
            errors=errors,
        )

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        """Handle a discovered Bluetooth device."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        
        # Pass the discovery info to the user step to pre-fill the form
        return await self.async_step_user({
            CONF_ADDRESS: discovery_info.address, 
            CONF_DEVICE_NAME: "Hughes Power Watchdog"
        })
