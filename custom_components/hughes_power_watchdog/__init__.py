import asyncio
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_ADDRESS
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_DEVICE_NAME
from .models import PowerWatchdogManager

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration."""
    address = entry.data[CONF_ADDRESS]
    name = entry.data[CONF_DEVICE_NAME]

    manager = PowerWatchdogManager(hass, address, name)
    
    task = entry.async_create_background_task(hass, manager.connect_loop(), "power_watchdog_loop")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "manager": manager,
        "task": task 
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        task = data["task"]
        
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    return unload_ok
