"""Config flow for the Hughes Power Watchdog integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

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

from .const import CONF_DEVICE_NAME, DEVICE_NAME_PREFIXES, DOMAIN

_LOGGER = logging.getLogger(__name__)


class PowerWatchdogConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Power Watchdog."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_DEVICE_NAME],
                data=user_input,
            )

        # Discover nearby Power Watchdog devices
        current_addresses = self._async_current_ids()
        discovered_devices: dict[str, str] = {}

        for service_info in async_discovered_service_info(self.hass):
            address = service_info.address
            name = service_info.name

            if address in current_addresses or address in discovered_devices:
                continue

            if name and any(name.startswith(p) for p in DEVICE_NAME_PREFIXES):
                discovered_devices[address] = f"{name} ({address})"

        if not discovered_devices:
            return self.async_abort(reason="no_devices_found")

        options = [
            {"value": addr, "label": label}
            for addr, label in discovered_devices.items()
        ]

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_DEVICE_NAME, default="Hughes Power Watchdog"
                ): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                data_schema, user_input
            ),
            errors=errors,
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> config_entries.ConfigFlowResult:
        """Handle a discovered Bluetooth device."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        return await self.async_step_user(
            {
                CONF_ADDRESS: discovery_info.address,
                CONF_DEVICE_NAME: "Hughes Power Watchdog",
            }
        )
