"""The room_hvac integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up room_hvac from a config entry."""
    
    # Initialize domain data structure
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Forward setup to climate platform
    await hass.config_entries.async_forward_entry_setup(entry, PLATFORMS)
    
    _LOGGER.info("Room HVAC integration setup complete for entry: %s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Clean up domain data
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.info("Room HVAC integration unloaded for entry: %s", entry.entry_id)
    
    return unload_ok