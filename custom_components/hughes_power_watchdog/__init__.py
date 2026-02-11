from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_ADDRESS
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_DEVICE_NAME
from .models import PowerWatchdogManager # Import the manager class

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration."""
    address = entry.data[CONF_ADDRESS]
    name = entry.data[CONF_DEVICE_NAME]

    manager = PowerWatchdogManager(hass, address, name)
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"manager": manager}

    entry.async_create_background_task(hass, manager.connect_loop(), "power_watchdog_loop")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
