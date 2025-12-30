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