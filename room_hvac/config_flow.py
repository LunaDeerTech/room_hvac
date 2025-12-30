"""Config flow for room_hvac integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.climate.const import DOMAIN as CLIMATE_DOMAIN, HVACMode
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .const import DOMAIN, AC_HVAC_MODES, FH_HVAC_MODES, PRESET_SLOTS

_LOGGER = logging.getLogger(__name__)


class EntityValidationError(HomeAssistantError):
    """Exception for entity validation errors."""
    pass


class RoomHVACConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for room_hvac."""
    
    VERSION = 1
    
    def __init__(self) -> None:
        """Initialize the config flow."""
        self._ac_entity_id: str | None = None
        self._fh_entity_id: str | None = None
        self._force_mode: bool = False
        self._ac_fan_modes: list[str] = []
        self._ac_presets: dict[str, dict[str, str]] = {}
        self._fh_min_temp: float | None = None
        self._fh_max_temp: float | None = None
        self._fh_presets: dict[str, dict[str, str]] = {}
        self._hass: HomeAssistant | None = None
    
    @property
    def hass(self) -> HomeAssistant:
        """Get HomeAssistant instance."""
        # ConfigFlow provides hass via the parent class
        # noinspection PyTypeChecker
        return super().hass  # type: ignore
    
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step - entity selection with capability validation."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            ac_entity_id = user_input.get("ac_entity_id")
            fh_entity_id = user_input.get("fh_entity_id")
            
            try:
                # Validate entities are provided
                if not ac_entity_id:
                    errors["ac_entity_id"] = "entity_required"
                if not fh_entity_id:
                    errors["fh_entity_id"] = "entity_required"
                
                # If entities are provided, validate them
                if ac_entity_id and fh_entity_id:
                    # Validate entities are different
                    if ac_entity_id == fh_entity_id:
                        errors["fh_entity_id"] = "entities_must_be_different"
                    
                    # Validate entity domains
                    if not self._validate_entity_domains(ac_entity_id, fh_entity_id):
                        errors["general"] = "invalid_domain"
                    
                    # If basic validation passed, check capabilities
                    if not errors:
                        # Get entity states from Home Assistant
                        ac_state = self.hass.states.get(ac_entity_id)
                        fh_state = self.hass.states.get(fh_entity_id)
                        
                        # Check if entities exist and are available
                        if not ac_state:
                            errors["ac_entity_id"] = "entity_not_found"
                        if not fh_state:
                            errors["fh_entity_id"] = "entity_not_found"
                        
                        # Check capabilities if states are available
                        if ac_state and fh_state:
                            # Validate AC capabilities
                            ac_capability_errors = self._validate_ac_capabilities(ac_state)
                            if ac_capability_errors:
                                errors.update(ac_capability_errors)
                            
                            # Validate FH capabilities
                            fh_capability_errors = self._validate_fh_capabilities(fh_state)
                            if fh_capability_errors:
                                errors.update(fh_capability_errors)
                    
                    # If all validations passed, store and proceed to next step
                    if not errors:
                        self._ac_entity_id = ac_entity_id
                        self._fh_entity_id = fh_entity_id
                        return await self.async_step_behavior()
            
            except Exception as ex:
                _LOGGER.error("Unexpected error during entity validation: %s", ex)
                errors["general"] = "validation_error"
        
        # Show the form with any errors
        return self.async_show_form(
            step_id="user",
            data_schema=self._get_user_schema(),
            errors=errors,
        )
    
    async def async_step_behavior(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the behavior options step - force mode configuration."""
        if user_input is not None:
            # Store force mode setting
            self._force_mode = user_input.get("force_mode", False)
            
            # Proceed to AC preset configuration
            return await self.async_step_ac_presets()
        
        # Show the behavior options form
        return self.async_show_form(
            step_id="behavior",
            data_schema=self._get_behavior_schema(),
        )
    
    async def async_step_ac_presets(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the AC preset configuration step."""
        if user_input is not None:
            # Process preset configurations
            self._ac_presets = {}
            
            for slot in PRESET_SLOTS:
                name = user_input.get(f"ac_{slot}_name")
                icon = user_input.get(f"ac_{slot}_icon")
                fan_speed = user_input.get(f"ac_{slot}_fan_speed")
                
                # Only store if name and fan_speed are provided
                if name and fan_speed:
                    self._ac_presets[name] = {
                        "fan_mode": fan_speed,
                        "icon": icon or "",  # Optional icon
                    }
            
            # Proceed to FH preset configuration
            return await self.async_step_fh_presets()
        
        # Get AC fan modes for the selector
        ac_state = self.hass.states.get(self._ac_entity_id)
        if ac_state:
            self._ac_fan_modes = ac_state.attributes.get("fan_modes", [])
        else:
            # Fallback - should not happen due to previous validation
            self._ac_fan_modes = []
        
        # Show the AC preset configuration form
        return self.async_show_form(
            step_id="ac_presets",
            data_schema=self._get_ac_presets_schema(),
        )
    
    async def async_step_fh_presets(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the FH preset configuration step."""
        if user_input is not None:
            # Process preset configurations
            self._fh_presets = {}
            
            for slot in PRESET_SLOTS:
                name = user_input.get(f"fh_{slot}_name")
                icon = user_input.get(f"fh_{slot}_icon")
                temperature = user_input.get(f"fh_{slot}_temp")
                
                # Only store if name and temperature are provided
                if name and temperature:
                    try:
                        temp_value = float(temperature)
                        
                        # Validate temperature is within FH range
                        if self._fh_min_temp is not None and temp_value < self._fh_min_temp:
                            _LOGGER.warning(
                                "FH preset temperature %s is below min %s, adjusting",
                                temp_value, self._fh_min_temp
                            )
                            temp_value = self._fh_min_temp
                        
                        if self._fh_max_temp is not None and temp_value > self._fh_max_temp:
                            _LOGGER.warning(
                                "FH preset temperature %s is above max %s, adjusting",
                                temp_value, self._fh_max_temp
                            )
                            temp_value = self._fh_max_temp
                        
                        self._fh_presets[name] = {
                            "temperature": str(temp_value),
                            "icon": icon or "",  # Optional icon
                        }
                    except (ValueError, TypeError):
                        _LOGGER.error(
                            "Invalid temperature value for FH preset %s: %s",
                            name, temperature
                        )
                        # Skip this preset if temperature is invalid
                        continue
            
            # All configuration complete - proceed to confirmation
            return await self.async_step_confirm()
        
        # Get FH temperature range for validation
        fh_state = self.hass.states.get(self._fh_entity_id)
        if fh_state:
            self._fh_min_temp = fh_state.attributes.get("min_temp")
            self._fh_max_temp = fh_state.attributes.get("max_temp")
        else:
            # Fallback - should not happen due to previous validation
            self._fh_min_temp = None
            self._fh_max_temp = None
        
        # Show the FH preset configuration form
        return self.async_show_form(
            step_id="fh_presets",
            data_schema=self._get_fh_presets_schema(),
        )
    
    def _validate_entity_domains(self, ac_entity_id: str, fh_entity_id: str) -> bool:
        """Validate that both entities belong to the climate domain."""
        return (
            ac_entity_id.startswith(f"{CLIMATE_DOMAIN}.") and
            fh_entity_id.startswith(f"{CLIMATE_DOMAIN}.")
        )
    
    def _validate_ac_capabilities(self, ac_state: State) -> dict[str, str]:
        """Validate that AC entity has required capabilities."""
        errors: dict[str, str] = {}
        
        # Check if entity supports fan modes
        fan_modes = ac_state.attributes.get("fan_modes", [])
        if not fan_modes:
            errors["ac_entity_id"] = "ac_no_fan_modes"
            return errors
        
        # Check if entity supports the required HVAC modes
        supported_modes = ac_state.attributes.get("hvac_modes", [])
        required_modes = [mode for mode in AC_HVAC_MODES if mode != HVACMode.OFF]
        
        # Check if AC supports at least one of cool/dry/fan_only
        if not any(mode in supported_modes for mode in required_modes):
            errors["ac_entity_id"] = "ac_missing_modes"
        
        # Check if entity supports target temperature (for cool/dry modes)
        if HVACMode.COOL not in supported_modes and HVACMode.DRY not in supported_modes:
            # If only fan_only is supported, temperature might not be required
            # But we'll still check if it has temperature capability
            if "target_temperature" not in ac_state.attributes:
                _LOGGER.warning("AC entity %s may not support target temperature", ac_state.entity_id)
        
        return errors
    
    def _validate_fh_capabilities(self, fh_state: State) -> dict[str, str]:
        """Validate that FH entity has required capabilities."""
        errors: dict[str, str] = {}
        
        # Check if entity supports heat mode
        supported_modes = fh_state.attributes.get("hvac_modes", [])
        if HVACMode.HEAT not in supported_modes:
            errors["fh_entity_id"] = "fh_no_heat_mode"
            return errors
        
        # Check if entity supports target temperature
        # This is critical for floor heating control
        if "target_temperature" not in fh_state.attributes:
            errors["fh_entity_id"] = "fh_no_target_temp"
            return errors
        
        # Check for temperature range if available
        min_temp = fh_state.attributes.get("min_temp")
        max_temp = fh_state.attributes.get("max_temp")
        if min_temp is None or max_temp is None:
            _LOGGER.warning("FH entity %s missing temperature range attributes", fh_state.entity_id)
        
        return errors
    
    def _get_user_schema(self) -> vol.Schema:
        """Generate the user step schema."""
        return vol.Schema(
            {
                vol.Required("ac_entity_id"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=CLIMATE_DOMAIN,
                        integration=CLIMATE_DOMAIN,
                    ),
                ),
                vol.Required("fh_entity_id"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=CLIMATE_DOMAIN,
                        integration=CLIMATE_DOMAIN,
                    ),
                ),
            }
        )
    
    def _get_behavior_schema(self) -> vol.Schema:
        """Generate the behavior options step schema."""
        return vol.Schema(
            {
                vol.Required("force_mode", default=False): selector.BooleanSelector(),
            }
        )
    
    def _get_ac_presets_schema(self) -> vol.Schema:
        """Generate the AC preset configuration schema with 4 slots."""
        schema_dict = {}
        
        for slot in PRESET_SLOTS:
            # Preset name (optional, but required if fan_speed is provided)
            schema_dict[vol.Optional(f"ac_{slot}_name")] = str
            
            # Preset icon (optional)
            schema_dict[vol.Optional(f"ac_{slot}_icon")] = str
            
            # Fan speed selector (optional, but required if name is provided)
            # Use SelectSelector with available fan modes
            if self._ac_fan_modes:
                schema_dict[vol.Optional(f"ac_{slot}_fan_speed")] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=self._ac_fan_modes,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            else:
                # Fallback to text input if no fan modes available
                schema_dict[vol.Optional(f"ac_{slot}_fan_speed")] = str
        
        return vol.Schema(schema_dict)
    
    def _get_fh_presets_schema(self) -> vol.Schema:
        """Generate the FH preset configuration schema with 4 slots."""
        schema_dict = {}
        
        for slot in PRESET_SLOTS:
            # Preset name (optional, but required if temperature is provided)
            schema_dict[vol.Optional(f"fh_{slot}_name")] = str
            
            # Preset icon (optional)
            schema_dict[vol.Optional(f"fh_{slot}_icon")] = str
            
            # Temperature selector (optional, but required if name is provided)
            # Use NumberSelector with range validation if available
            if self._fh_min_temp is not None and self._fh_max_temp is not None:
                schema_dict[vol.Optional(f"fh_{slot}_temp")] = selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=self._fh_min_temp,
                        max=self._fh_max_temp,
                        step=0.5,
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                )
            else:
                # Fallback to text input with basic validation
                schema_dict[vol.Optional(f"fh_{slot}_temp")] = vol.All(
                    vol.Coerce(float),
                    vol.Range(min=5, max=35)  # Reasonable defaults
                )
        
        return vol.Schema(schema_dict)
    
    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 5: Confirm configuration and create entry.
        
        Shows a summary of all configuration options and creates the config entry
        upon confirmation. No further modifications are allowed in this step.
        """
        if user_input is not None:
            # User confirmed - create the config entry
            # Prepare the configuration data
            config_data = self._build_config_data()
            
            # Create unique ID for this entry
            await self.async_set_unique_id(f"{self._ac_entity_id}_{self._fh_entity_id}")
            self._abort_if_unique_id_configured()
            
            # Create the config entry
            return self.async_create_entry(
                title=f"Room HVAC - {self._ac_entity_id.split('.')[-1]}",
                data=config_data,
            )
        
        # Build configuration summary for display
        summary = self._build_configuration_summary()
        
        # Show confirmation form with summary
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({vol.Required("confirm"): bool}),
            description_placeholders=summary,
        )
    
    def _build_config_data(self) -> dict[str, Any]:
        """Build the final configuration data structure.
        
        Returns a dictionary with all configuration data needed for the integration.
        """
        # Filter out empty presets (presets with missing required values)
        ac_presets = {
            k: v for k, v in self._ac_presets.items() 
            if v.get("fan_mode")  # AC preset needs fan_mode
        }
        fh_presets = {
            k: v for k, v in self._fh_presets.items() 
            if v.get("temperature")  # FH preset needs temperature
        }
        
        return {
            "ac_entity_id": self._ac_entity_id,
            "fh_entity_id": self._fh_entity_id,
            "force_mode": self._force_mode,
            "ac_presets": ac_presets,
            "fh_presets": fh_presets,
        }
    
    def _build_configuration_summary(self) -> dict[str, str]:
        """Build a human-readable summary of the configuration.
        
        Returns a dictionary of placeholders for the confirmation form.
        """
        summary = {
            "ac_entity": self._ac_entity_id or "Not selected",
            "fh_entity": self._fh_entity_id or "Not selected",
            "force_mode": "Enabled" if self._force_mode else "Disabled",
        }
        
        # AC Presets summary
        ac_preset_lines = []
        for preset_name, preset_data in self._ac_presets.items():
            fan_mode = preset_data.get("fan_mode", "")
            icon = preset_data.get("icon", "")
            if icon:
                ac_preset_lines.append(f"  • {icon} {preset_name}: {fan_mode}")
            else:
                ac_preset_lines.append(f"  • {preset_name}: {fan_mode}")
        summary["ac_presets"] = "\n".join(ac_preset_lines) if ac_preset_lines else "  • No presets configured"
        
        # FH Presets summary
        fh_preset_lines = []
        for preset_name, preset_data in self._fh_presets.items():
            temperature = preset_data.get("temperature", "")
            icon = preset_data.get("icon", "")
            if icon:
                fh_preset_lines.append(f"  • {icon} {preset_name}: {temperature}°C")
            else:
                fh_preset_lines.append(f"  • {preset_name}: {temperature}°C")
        summary["fh_presets"] = "\n".join(fh_preset_lines) if fh_preset_lines else "  • No presets configured"
        
        return summary