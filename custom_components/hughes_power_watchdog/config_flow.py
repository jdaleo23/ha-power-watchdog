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

from .const import CONF_BLE_NAME, CONF_DEVICE_NAME, DEVICE_NAME_PREFIXES, DOMAIN

_LOGGER = logging.getLogger(__name__)


class PowerWatchdogConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Power Watchdog."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the config flow."""
        self._discovered_address: str | None = None
        self._discovered_ble_name: str | None = None

    # ── Manual / user-initiated setup ────────────────────────────────────────

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step when the user adds the integration manually."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()

            # Look up the raw BLE name from the discovered service info so we
            # can store it for model detection later.
            ble_name = ""
            for service_info in async_discovered_service_info(self.hass):
                if service_info.address == address:
                    ble_name = service_info.name or ""
                    break

            return self.async_create_entry(
                title=user_input[CONF_DEVICE_NAME],
                data={
                    CONF_ADDRESS: address,
                    CONF_DEVICE_NAME: user_input[CONF_DEVICE_NAME],
                    CONF_BLE_NAME: ble_name,
                },
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

    # ── Bluetooth auto-discovery ──────────────────────────────────────────────

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> config_entries.ConfigFlowResult:
        """Handle a Bluetooth-discovered device."""
        address = discovery_info.address
        ble_name = discovery_info.name or ""

        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()

        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.data.get(CONF_ADDRESS) == address:
                return self.async_abort(reason="already_configured")

        self._discovered_address = address
        self._discovered_ble_name = ble_name
        self.context["title_placeholders"] = {"name": ble_name}

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Confirm step for a Bluetooth-discovered device."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_DEVICE_NAME],
                data={
                    CONF_ADDRESS: self._discovered_address,
                    CONF_DEVICE_NAME: user_input[CONF_DEVICE_NAME],
                    CONF_BLE_NAME: self._discovered_ble_name,  # store raw BLE name
                },
            )

        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._discovered_ble_name,
                "address": self._discovered_address,
            },
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_NAME, default="Hughes Power Watchdog"
                    ): str,
                }
            ),
        )
