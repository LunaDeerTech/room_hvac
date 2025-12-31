"""Constants for room_hvac integration."""
from __future__ import annotations

from homeassistant.components.climate.const import HVACMode

# Domain identifier
DOMAIN = "room_hvac"

# Supported HVAC modes list
SUPPORTED_HVAC_MODES = [
    HVACMode.OFF,
    HVACMode.COOL,
    HVACMode.DRY,
    HVACMode.FAN_ONLY,
    HVACMode.HEAT,
]

# Air conditioner modes (cool / dry / fan_only) - route to AC device
AC_HVAC_MODES = {HVACMode.COOL, HVACMode.DRY, HVACMode.FAN_ONLY}

# Floor heating modes (heat) - route to floor heating device
FH_HVAC_MODES = {HVACMode.HEAT}

# Preset slot internal identifiers
PRESET_SLOT_1 = "slot_1"
PRESET_SLOT_2 = "slot_2"
PRESET_SLOT_3 = "slot_3"
PRESET_SLOT_4 = "slot_4"

# All preset slots as a list for iteration
PRESET_SLOTS = [PRESET_SLOT_1, PRESET_SLOT_2, PRESET_SLOT_3, PRESET_SLOT_4]

# Configuration keys
CONF_AC_ENTITY_ID = "ac_entity_id"
CONF_FH_ENTITY_ID = "fh_entity_id"
CONF_FORCE_MODE = "force_mode"
CONF_AC_PRESETS = "ac_presets"
CONF_FH_PRESETS = "fh_presets"

# AC preset default values
AC_PRESET_DEFAULTS = {
    PRESET_SLOT_1: {"name": "自动", "icon": "mdi:fan-auto"},
    PRESET_SLOT_2: {"name": "静音", "icon": "mdi:weather-night"},
    PRESET_SLOT_3: {"name": "中速", "icon": "mdi:speedometer-medium"},
    PRESET_SLOT_4: {"name": "全速", "icon": "mdi:speedometer"},
}

# FH preset default values
FH_PRESET_DEFAULTS = {
    PRESET_SLOT_1: {"name": "外出", "icon": "mdi:account-arrow-left-outline"},
    PRESET_SLOT_2: {"name": "在家", "icon": "mdi:home"},
    PRESET_SLOT_3: {"name": "活动", "icon": "mdi:dumbbell"},
    PRESET_SLOT_4: {"name": "睡眠", "icon": "mdi:bed"},
}