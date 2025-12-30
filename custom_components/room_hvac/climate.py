"""Climate platform for room_hvac integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, Event, CALLBACK_TYPE
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN, SUPPORTED_HVAC_MODES, AC_HVAC_MODES, FH_HVAC_MODES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the room_hvac climate platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RoomHVACClimateEntity(entry.entry_id, data)])


class RoomHVACClimateEntity(ClimateEntity):
    """Representation of a room_hvac climate entity."""
    
    # Core entity properties - using constants from const.py
    _attr_hvac_modes = SUPPORTED_HVAC_MODES
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1.0
    
    def __init__(self, entry_id: str, data: dict[str, Any]) -> None:
        """Initialize the room_hvac climate entity."""
        self._entry_id = entry_id
        self._data = data
        
        # Entity identity
        self._attr_name = "Room HVAC"
        self._attr_unique_id = f"room_hvac_{entry_id}"
        
        # Initial state - default to off as specified
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_preset_mode = None
        self._attr_target_temperature = None
        self._attr_current_temperature = None
        
        # State change listeners and tracking
        self._listeners: dict[str, CALLBACK_TYPE] = {}
        self._last_internal_update: dict[str, float] = {}  # timestamp of last internal update
        self._is_external_update = False  # Flag to detect external modifications
        self._correction_in_progress: dict[str, bool] = {}  # Prevent recursive corrections
    
    async def async_added_to_hass(self) -> None:
        """Set up state change listeners when entity is added to Home Assistant."""
        await super().async_added_to_hass()
        
        # Get AC and FH entity IDs from config
        ac_entity_id = self._data.get("ac_entity_id")
        fh_entity_id = self._data.get("fh_entity_id")
        
        # Set up state change listeners for both devices
        if ac_entity_id:
            self._listeners[ac_entity_id] = async_track_state_change_event(
                self.hass,
                [ac_entity_id],
                self._handle_state_change,
            )
            _LOGGER.debug("Setup state listener for AC: %s", ac_entity_id)
        
        if fh_entity_id:
            self._listeners[fh_entity_id] = async_track_state_change_event(
                self.hass,
                [fh_entity_id],
                self._handle_state_change,
            )
            _LOGGER.debug("Setup state listener for FH: %s", fh_entity_id)
        
        _LOGGER.info("State change listeners initialized for entry: %s", self._entry_id)
    
    def _handle_state_change(self, event: Event) -> None:
        """Handle state changes from downstream AC/FH devices."""
        entity_id = event.data.get("entity_id")
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        
        if not entity_id or not new_state:
            return
        
        # Loop protection: Check if a correction is already in progress for this device
        if self._correction_in_progress.get(entity_id, False):
            _LOGGER.debug(
                "Ignoring state change from %s - correction already in progress", 
                entity_id
            )
            return
        
        # Check if this is an internal update (from our entity)
        current_time = self.hass.loop.time()
        last_update = self._last_internal_update.get(entity_id, 0)
        
        # If update happened very recently (within 2 seconds), it's likely internal
        if current_time - last_update < 2.0:
            _LOGGER.debug(
                "Ignoring state change from %s - recent internal update detected", 
                entity_id
            )
            return
        
        # External modification detected
        self._is_external_update = True
        _LOGGER.info(
            "External modification detected on %s: %s -> %s",
            entity_id,
            old_state.state if old_state else "None",
            new_state.state
        )
        
        # Check if force mode is enabled and enforce consistency
        if self._is_force_mode_enabled():
            try:
                self._enforce_force_mode_consistency(entity_id, new_state)
            except Exception as e:
                _LOGGER.error(
                    "Force mode enforcement failed for %s: %s", 
                    entity_id, e
                )
                # Reset flags before raising
                self._is_external_update = False
                self._correction_in_progress[entity_id] = False
                raise
            finally:
                # Ensure flag is reset even if correction succeeds
                self._correction_in_progress[entity_id] = False
        else:
            # Normal mode: just sync our state
            self._sync_from_device(entity_id, new_state)
        
        # Reset flag after processing
        self._is_external_update = False
    
    def _is_force_mode_enabled(self) -> bool:
        """Check if force mode is enabled in config."""
        return self._data.get("force_mode", False)
    
    def _enforce_force_mode_consistency(self, entity_id: str, state) -> None:
        """Enforce strict consistency when force mode is enabled."""
        ac_entity_id = self._data.get("ac_entity_id")
        fh_entity_id = self._data.get("fh_entity_id")
        
        # Determine which device this is
        is_ac = entity_id == ac_entity_id
        is_fh = entity_id == fh_entity_id
        
        if not (is_ac or is_fh):
            return
        
        # Get expected state based on our current mode
        expected_hvac_mode = self._get_expected_device_mode_for(entity_id)
        expected_target_temp = self._get_expected_target_temperature()
        
        # Check for inconsistencies
        inconsistencies = []
        
        # Check HVAC mode consistency
        actual_hvac_mode = state.state
        if actual_hvac_mode != expected_hvac_mode:
            inconsistencies.append(
                f"HVAC mode mismatch: expected {expected_hvac_mode}, got {actual_hvac_mode}"
            )
        
        # Check temperature consistency (only if not in fan_only or off mode)
        if (expected_hvac_mode not in [HVACMode.OFF, HVACMode.FAN_ONLY] and 
            expected_target_temp is not None):
            
            actual_target_temp = state.attributes.get("temperature")
            if actual_target_temp is not None and actual_target_temp != expected_target_temp:
                inconsistencies.append(
                    f"Temperature mismatch: expected {expected_target_temp}, got {actual_target_temp}"
                )
        
        if inconsistencies:
            _LOGGER.warning(
                "Force mode inconsistency detected on %s: %s",
                entity_id,
                "; ".join(inconsistencies)
            )
            # Set correction flag to prevent recursive calls
            self._correction_in_progress[entity_id] = True
            # Immediately correct the inconsistency
            self._correct_inconsistency(entity_id, expected_hvac_mode, expected_target_temp)
        else:
            _LOGGER.debug(
                "Force mode consistency check passed for %s",
                entity_id
            )
    
    def _get_expected_device_mode_for(self, entity_id: str) -> str:
        """Get the expected HVAC mode for a specific device based on our current state."""
        ac_entity_id = self._data.get("ac_entity_id")
        fh_entity_id = self._data.get("fh_entity_id")
        
        # If this device should not be active, it should be OFF
        if entity_id == ac_entity_id:
            if self._attr_hvac_mode in AC_HVAC_MODES:
                return self._attr_hvac_mode
        elif entity_id == fh_entity_id:
            if self._attr_hvac_mode in FH_HVAC_MODES:
                return self._attr_hvac_mode
        
        return HVACMode.OFF
    
    def _get_expected_target_temperature(self) -> float | None:
        """Get the expected target temperature for the active device."""
        # Only return if we have a target temperature and are in a temperature-supporting mode
        if (self._attr_hvac_mode in [HVACMode.COOL, HVACMode.DRY, HVACMode.HEAT] and 
            self._attr_target_temperature is not None):
            return self._attr_target_temperature
        return None
    
    def _correct_inconsistency(self, entity_id: str, expected_mode: str, expected_temp: float | None) -> None:
        """Immediately correct an inconsistency in force mode."""
        _LOGGER.info(
            "Force mode: correcting %s to mode=%s, temp=%s",
            entity_id,
            expected_mode,
            expected_temp
        )
        
        # Record this as an internal update to prevent feedback loops
        self._record_internal_update(entity_id, "force_mode_correction")
        
        try:
            # First, set the HVAC mode
            self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {"entity_id": entity_id, "hvac_mode": expected_mode},
                blocking=True,
            )
            
            # Then, if needed, set the temperature
            if expected_temp is not None and expected_mode != HVACMode.FAN_ONLY:
                self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {"entity_id": entity_id, "temperature": expected_temp},
                    blocking=True,
                )
            
            _LOGGER.info(
                "Force mode correction successful for %s",
                entity_id
            )
            
        except Exception as e:
            _LOGGER.error(
                "Force mode correction FAILED for %s: %s",
                entity_id,
                e
            )
            # Re-raise to propagate the error
            raise
    
    async def _validate_force_mode_consistency_after_change(self) -> None:
        """Validate that all devices are in correct state after a mode change in force mode."""
        ac_entity_id = self._data.get("ac_entity_id")
        fh_entity_id = self._data.get("fh_entity_id")
        
        # Check AC device if it should be active
        if ac_entity_id:
            ac_state = self.hass.states.get(ac_entity_id)
            if ac_state:
                expected_ac_mode = self._get_expected_device_mode_for(ac_entity_id)
                actual_ac_mode = ac_state.state
                
                if actual_ac_mode != expected_ac_mode:
                    _LOGGER.warning(
                        "Force mode: AC state inconsistency after mode change - expected %s, got %s",
                        expected_ac_mode,
                        actual_ac_mode
                    )
                    # Set correction flag to prevent listener feedback during self-validation
                    self._correction_in_progress[ac_entity_id] = True
                    try:
                        self._correct_inconsistency(ac_entity_id, expected_ac_mode, self._get_expected_target_temperature())
                    finally:
                        self._correction_in_progress[ac_entity_id] = False
        
        # Check FH device if it should be active
        if fh_entity_id:
            fh_state = self.hass.states.get(fh_entity_id)
            if fh_state:
                expected_fh_mode = self._get_expected_device_mode_for(fh_entity_id)
                actual_fh_mode = fh_state.state
                
                if actual_fh_mode != expected_fh_mode:
                    _LOGGER.warning(
                        "Force mode: FH state inconsistency after mode change - expected %s, got %s",
                        expected_fh_mode,
                        actual_fh_mode
                    )
                    # Set correction flag to prevent listener feedback during self-validation
                    self._correction_in_progress[fh_entity_id] = True
                    try:
                        self._correct_inconsistency(fh_entity_id, expected_fh_mode, self._get_expected_target_temperature())
                    finally:
                        self._correction_in_progress[fh_entity_id] = False
    
    async def async_will_remove_hass(self) -> None:
        """Clean up listeners when entity is removed."""
        for entity_id, remove_listener in self._listeners.items():
            remove_listener()
            _LOGGER.debug("Removed state listener for: %s", entity_id)
        self._listeners.clear()
        self._last_internal_update.clear()
        self._correction_in_progress.clear()
        _LOGGER.info("State change listeners cleaned up for entry: %s", self._entry_id)
    
    def _record_internal_update(self, entity_id: str, context: str = "unknown") -> None:
        """Record that we're about to update a device internally."""
        current_time = self.hass.loop.time()
        self._last_internal_update[entity_id] = current_time
        _LOGGER.debug("Recorded internal update for: %s (context: %s, time: %.2f)", entity_id, context, current_time)
    
    def _sync_from_device(self, entity_id: str, state) -> None:
        """Sync our entity state from the downstream device state."""
        # Force mode disables automatic syncing - corrections are handled separately
        if self._is_force_mode_enabled():
            _LOGGER.debug(
                "Force mode enabled - skipping automatic sync from %s",
                entity_id
            )
            return
        
        # Only sync if this device is currently active
        ac_entity_id = self._data.get("ac_entity_id")
        fh_entity_id = self._data.get("fh_entity_id")
        
        is_ac_active = self._attr_hvac_mode in AC_HVAC_MODES and entity_id == ac_entity_id
        is_fh_active = self._attr_hvac_mode in FH_HVAC_MODES and entity_id == fh_entity_id
        
        if not (is_ac_active or is_fh_active):
            # Device is not currently active, no need to sync
            return
        
        # Sync HVAC mode if it changed
        new_hvac_mode = state.state
        if new_hvac_mode != self._attr_hvac_mode:
            _LOGGER.info(
                "Syncing HVAC mode from %s to %s",
                self._attr_hvac_mode,
                new_hvac_mode
            )
            self._attr_hvac_mode = new_hvac_mode
        
        # Sync temperature attributes
        if state.attributes:
            # Current temperature
            current_temp = state.attributes.get("current_temperature")
            if current_temp is not None:
                self._attr_current_temperature = current_temp
            
            # Target temperature (only if not in fan_only mode)
            if self._attr_hvac_mode != HVACMode.FAN_ONLY:
                target_temp = state.attributes.get("temperature")
                if target_temp is not None:
                    self._attr_target_temperature = target_temp
            
            # Preset mode
            preset = state.attributes.get("preset_mode")
            if preset is not None:
                self._attr_preset_mode = preset
        
        # Update HA state
        self.async_write_ha_state()
    
    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature from the active device."""
        ac_entity_id = self._data.get("ac_entity_id")
        fh_entity_id = self._data.get("fh_entity_id")
        
        if self._attr_hvac_mode in AC_HVAC_MODES and ac_entity_id:
            ac_state = self.hass.states.get(ac_entity_id)
            if ac_state:
                return ac_state.attributes.get("current_temperature")
        
        elif self._attr_hvac_mode in FH_HVAC_MODES and fh_entity_id:
            fh_state = self.hass.states.get(fh_entity_id)
            if fh_state:
                return fh_state.attributes.get("current_temperature")
        
        # Off mode or no active device
        return None
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes for debugging."""
        # Get correction status for debugging
        ac_entity_id = self._data.get("ac_entity_id")
        fh_entity_id = self._data.get("fh_entity_id")
        ac_correcting = self._correction_in_progress.get(ac_entity_id, False) if ac_entity_id else False
        fh_correcting = self._correction_in_progress.get(fh_entity_id, False) if fh_entity_id else False
        
        return {
            "entry_id": self._entry_id,
            "force_mode": self._data.get("force_mode", False),
            "ac_entity_id": ac_entity_id,
            "fh_entity_id": fh_entity_id,
            "active_device": self._get_active_device_name(),
            "ac_correcting": ac_correcting,
            "fh_correcting": fh_correcting,
            "listener_count": len(self._listeners),
        }
    
    def _get_active_device_name(self) -> str | None:
        """Get the name of the currently active device."""
        if self._attr_hvac_mode in AC_HVAC_MODES:
            return "AC"
        elif self._attr_hvac_mode in FH_HVAC_MODES:
            return "FH"
        return None
    
    @property
    def preset_modes(self) -> list[str] | None:
        """Return list of available preset modes based on current HVAC mode."""
        # Off mode - no presets available
        if self._attr_hvac_mode == HVACMode.OFF:
            return []
        
        # AC modes - return AC presets
        if self._attr_hvac_mode in AC_HVAC_MODES:
            ac_presets = self._data.get("ac_presets", {})
            return list(ac_presets.keys())
        
        # Heat mode - return FH presets
        if self._attr_hvac_mode in FH_HVAC_MODES:
            fh_presets = self._data.get("fh_presets", {})
            return list(fh_presets.keys())
        
        return []
    
    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new hvac mode with routing logic to AC/FH devices."""
        _LOGGER.info("Setting HVAC mode to %s", hvac_mode)
        
        # Step 1: Turn off current device if switching modes
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._turn_off_current_device()
        
        # Step 2: Update local mode
        self._attr_hvac_mode = hvac_mode
        
        # Step 3: Route to appropriate device
        if hvac_mode in AC_HVAC_MODES:
            await self._route_to_ac(hvac_mode)
        elif hvac_mode in FH_HVAC_MODES:
            await self._route_to_fh(hvac_mode)
        elif hvac_mode == HVACMode.OFF:
            # Off mode - ensure all devices are off (already done in step 1)
            self._attr_target_temperature = None
            self._attr_current_temperature = None
            self._attr_preset_mode = None
            _LOGGER.info("All devices turned off")
        
        # Step 4: Update state
        await self._update_active_device_state()
        self.async_write_ha_state()
        
        # Step 5: Force mode validation (if enabled)
        if self._is_force_mode_enabled():
            await self._validate_force_mode_consistency_after_change()
    
    async def _turn_off_current_device(self) -> None:
        """Turn off the currently active device."""
        ac_entity_id = self._data.get("ac_entity_id")
        fh_entity_id = self._data.get("fh_entity_id")
        
        if self._attr_hvac_mode in AC_HVAC_MODES and ac_entity_id:
            # Turn off AC
            try:
                self._record_internal_update(ac_entity_id, "turn_off_before_mode_switch")
                await self.hass.services.async_call(
                    "climate",
                    "set_hvac_mode",
                    {"entity_id": ac_entity_id, "hvac_mode": HVACMode.OFF},
                    blocking=True,
                )
                _LOGGER.info("Turned off AC device: %s", ac_entity_id)
            except Exception as e:
                _LOGGER.error("Failed to turn off AC %s: %s", ac_entity_id, e)
                raise
        
        elif self._attr_hvac_mode in FH_HVAC_MODES and fh_entity_id:
            # Turn off FH
            try:
                self._record_internal_update(fh_entity_id, "turn_off_before_mode_switch")
                await self.hass.services.async_call(
                    "climate",
                    "set_hvac_mode",
                    {"entity_id": fh_entity_id, "hvac_mode": HVACMode.OFF},
                    blocking=True,
                )
                _LOGGER.info("Turned off FH device: %s", fh_entity_id)
            except Exception as e:
                _LOGGER.error("Failed to turn off FH %s: %s", fh_entity_id, e)
                raise
    
    async def _route_to_ac(self, hvac_mode: str) -> None:
        """Route to AC device with specified mode."""
        ac_entity_id = self._data.get("ac_entity_id")
        if not ac_entity_id:
            _LOGGER.error("AC entity not configured")
            raise ValueError("AC entity not configured")
        
        try:
            self._record_internal_update(ac_entity_id, "route_to_ac")
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {"entity_id": ac_entity_id, "hvac_mode": hvac_mode},
                blocking=True,
            )
            _LOGGER.info("Routed to AC with mode %s: %s", hvac_mode, ac_entity_id)
        except Exception as e:
            _LOGGER.error("Failed to route to AC %s: %s", ac_entity_id, e)
            raise
    
    async def _route_to_fh(self, hvac_mode: str) -> None:
        """Route to FH device with specified mode."""
        fh_entity_id = self._data.get("fh_entity_id")
        if not fh_entity_id:
            _LOGGER.error("FH entity not configured")
            raise ValueError("FH entity not configured")
        
        try:
            self._record_internal_update(fh_entity_id, "route_to_fh")
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {"entity_id": fh_entity_id, "hvac_mode": hvac_mode},
                blocking=True,
            )
            _LOGGER.info("Routed to FH with mode %s: %s", hvac_mode, fh_entity_id)
        except Exception as e:
            _LOGGER.error("Failed to route to FH %s: %s", fh_entity_id, e)
            raise
    
    async def _update_active_device_state(self) -> None:
        """Update target temperature from active device (current temp is handled by property)."""
        ac_entity_id = self._data.get("ac_entity_id")
        fh_entity_id = self._data.get("fh_entity_id")
        
        if self._attr_hvac_mode in AC_HVAC_MODES and ac_entity_id:
            # Get AC state
            ac_state = self.hass.states.get(ac_entity_id)
            if ac_state:
                # Preserve target temperature if already set
                if self._attr_target_temperature is None:
                    self._attr_target_temperature = ac_state.attributes.get("temperature")
                _LOGGER.debug("Updated AC target temp: %s", self._attr_target_temperature)
        
        elif self._attr_hvac_mode in FH_HVAC_MODES and fh_entity_id:
            # Get FH state
            fh_state = self.hass.states.get(fh_entity_id)
            if fh_state:
                # Preserve target temperature if already set
                if self._attr_target_temperature is None:
                    self._attr_target_temperature = fh_state.attributes.get("temperature")
                _LOGGER.debug("Updated FH target temp: %s", self._attr_target_temperature)
    
    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature to active device."""
        if ATTR_TEMPERATURE not in kwargs:
            return
        
        temperature = kwargs[ATTR_TEMPERATURE]
        
        # Ignore for fan_only mode
        if self._attr_hvac_mode == HVACMode.FAN_ONLY:
            _LOGGER.info("Ignoring temperature set in fan_only mode")
            return
        
        # Route to active device
        ac_entity_id = self._data.get("ac_entity_id")
        fh_entity_id = self._data.get("fh_entity_id")
        
        if self._attr_hvac_mode in AC_HVAC_MODES and ac_entity_id:
            try:
                self._record_internal_update(ac_entity_id, "set_temperature")
                await self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {"entity_id": ac_entity_id, "temperature": temperature},
                    blocking=True,
                )
                self._attr_target_temperature = temperature
                _LOGGER.info("Set AC temperature to %s", temperature)
            except Exception as e:
                _LOGGER.error("Failed to set AC temperature: %s", e)
                raise
        
        elif self._attr_hvac_mode in FH_HVAC_MODES and fh_entity_id:
            try:
                self._record_internal_update(fh_entity_id, "set_temperature")
                await self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {"entity_id": fh_entity_id, "temperature": temperature},
                    blocking=True,
                )
                self._attr_target_temperature = temperature
                _LOGGER.info("Set FH temperature to %s", temperature)
            except Exception as e:
                _LOGGER.error("Failed to set FH temperature: %s", e)
                raise
        
        self.async_write_ha_state()
        
        # Force mode validation after temperature change
        if self._is_force_mode_enabled():
            await self._validate_force_mode_consistency_after_change()
    
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode with proper routing based on current HVAC mode."""
        _LOGGER.info("Setting preset mode to %s", preset_mode)
        
        # Get preset configurations
        ac_presets = self._data.get("ac_presets", {})
        fh_presets = self._data.get("fh_presets", {})
        
        # Route preset based on current HVAC mode
        if self._attr_hvac_mode in AC_HVAC_MODES:
            # AC mode - apply fan_mode from AC preset
            if preset_mode in ac_presets:
                preset_data = ac_presets[preset_mode]
                fan_mode = preset_data.get("fan_mode")
                
                if fan_mode:
                    ac_entity_id = self._data.get("ac_entity_id")
                    if ac_entity_id:
                        try:
                            self._record_internal_update(ac_entity_id, "set_preset_ac")
                            await self.hass.services.async_call(
                                "climate",
                                "set_fan_mode",
                                {"entity_id": ac_entity_id, "fan_mode": fan_mode},
                                blocking=True,
                            )
                            self._attr_preset_mode = preset_mode
                            _LOGGER.info("Applied AC preset %s with fan_mode %s", preset_mode, fan_mode)
                        except Exception as e:
                            _LOGGER.error("Failed to apply AC preset %s: %s", preset_mode, e)
                            raise
            else:
                _LOGGER.warning("Preset %s not found in AC presets", preset_mode)
        
        elif self._attr_hvac_mode in FH_HVAC_MODES:
            # Heat mode - apply temperature from FH preset
            if preset_mode in fh_presets:
                preset_data = fh_presets[preset_mode]
                temperature_str = preset_data.get("temperature")
                
                if temperature_str:
                    try:
                        temperature = float(temperature_str)
                        fh_entity_id = self._data.get("fh_entity_id")
                        if fh_entity_id:
                            self._record_internal_update(fh_entity_id, "set_preset_fh")
                            await self.hass.services.async_call(
                                "climate",
                                "set_temperature",
                                {"entity_id": fh_entity_id, "temperature": temperature},
                                blocking=True,
                            )
                            self._attr_preset_mode = preset_mode
                            self._attr_target_temperature = temperature
                            _LOGGER.info("Applied FH preset %s with temperature %s", preset_mode, temperature)
                    except (ValueError, TypeError) as e:
                        _LOGGER.error("Invalid temperature in preset %s: %s", preset_mode, e)
                        raise
                    except Exception as e:
                        _LOGGER.error("Failed to apply FH preset %s: %s", preset_mode, e)
                        raise
            else:
                _LOGGER.warning("Preset %s not found in FH presets", preset_mode)
        
        elif self._attr_hvac_mode == HVACMode.OFF:
            # Off mode - no presets should be available
            _LOGGER.warning("Cannot set preset mode %s when HVAC mode is OFF", preset_mode)
            return
        
        # Update state
        self.async_write_ha_state()
        
        # Force mode validation after preset change
        if self._is_force_mode_enabled():
            await self._validate_force_mode_consistency_after_change()