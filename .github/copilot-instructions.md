# Copilot Instructions for room_hvac

**Architecture**: Single climate entity → routes to AC or floor heating. Never both active.

**Critical Rules**:
- `AC_HVAC_MODES = {COOL, DRY, FAN_ONLY}` → AC device
- `FH_HVAC_MODES = {HEAT}` → FH device  
- Turn OFF previous device BEFORE activating new one
- Temperature ALWAYS fetched from active device (no caching)
- Use `blocking=True` for ALL service calls
- Validate everything in config flow, nothing at runtime

**File Structure**:
- `climate.py` - Mode routing, state sync, presets (main logic)
- `config_flow.py` - 5-step validation wizard  
- `const.py` - Constants only
- `__init__.py` - Setup/unload only

**Key Pattern** (mode switching):
```python
async def async_set_hvac_mode(self, hvac_mode: str) -> None:
    if self._attr_hvac_mode != HVACMode.OFF:
        await self._turn_off_current_device()  # CRITICAL: immediate off
    
    self._attr_hvac_mode = hvac_mode
    
    if hvac_mode in AC_HVAC_MODES:
        await self._route_to_ac(hvac_mode)
    elif hvac_mode in FH_HVAC_MODES:
        await self._route_to_fh(hvac_mode)
    
    await self._update_active_device_state()
    self.async_write_ha_state()
```

**Presets**: Dynamic visibility by mode
- AC modes: show AC fan presets only
- Heat mode: show FH temperature presets only
- Off mode: no presets

**Debug**: `tail -f home-assistant.log | grep "room_hvac"`

**Never**:
- Cache temperature
- Allow AC + FH both on
- Change mode routing constants
- Skip config flow validation

**Always**:
- Use blocking=True
- Record internal updates
- Filter empty preset slots
- Turn off previous device first

## Development Rules

### ✅ DO
- Use existing constants from `const.py`
- Follow routing patterns in `climate.py`
- Add validation in config flow steps
- Update `strings.json` for new user messages
- Test routing logic immediately in HA
- Use `blocking=True` for all service calls
- Log all operations with appropriate levels
- Preserve existing preset slot structure (slot_1 to slot_4)

### ❌ DON'T
- Add new HVAC modes beyond the 5 specified
- Allow simultaneous AC + FH activation
- Cache temperature values (always fetch from active device)
- Create subdirectories in integration root
- Use Chinese in Python code/comments
- Modify entity IDs or unique ID format
- Skip error handling in service calls
- Change preset slot naming conventions

## Key Implementation Details

### State Management
- **No state caching**: Temperature values are always fetched from the active device
- **Immediate device turn-off**: When switching modes, the previous device is turned off before activating the new one
- **Force mode**: Optional configuration that prevents external changes to the unified entity
- **Active device tracking**: `_get_active_device_name()` returns "AC", "FH", or None

### Preset System
- **Dynamic visibility**: Preset list changes based on current HVAC mode
- **AC presets**: Map to fan modes (4 slots: slot_1 to slot_4)
- **FH presets**: Map to target temperatures (4 slots: slot_1 to slot_4)
- **Empty slot handling**: Unconfigured slots are automatically hidden
- **Preset data structure**: `{preset_name: {"fan_mode": "value", "icon": "optional"}}` for AC
- **Preset data structure**: `{preset_name: {"temperature": "value", "icon": "optional"}}` for FH

### Config Flow (5 steps)
1. **Entity Selection** (`async_step_user`): Choose AC and FH climate entities with validation
   - Validates entity domains (must be climate.*)
   - Validates capabilities (fan_modes, hvac_modes, target_temperature)
   - Ensures entities are different
2. **Behavior Options** (`async_step_behavior`): Configure force control mode
3. **AC Presets** (`async_step_ac_presets`): Set up fan speed presets (4 slots)
   - Retrieves available fan_modes from AC entity
   - Stores only configured slots (name + fan_speed required)
4. **FH Presets** (`async_step_fh_presets`): Set up temperature presets (4 slots)
   - Validates temperatures against min/max range
   - Adjusts out-of-range values with warnings
   - Stores only configured slots (name + temperature required)
5. **Confirmation** (`async_step_confirm`): Review and create entry

### Validation Patterns
- **Entity existence**: Check states are available and not unavailable
- **Domain validation**: Both must be `climate.*` entities
- **AC capabilities**: Must have `fan_modes` and support cool/dry/fan_only
- **FH capabilities**: Must support `heat` mode and `target_temperature`
- **Temperature range**: Validate against entity's min_temp/max_temp attributes

### Debugging
```bash
# Monitor routing decisions
tail -f home-assistant.log | grep "room_hvac"

# Check entity state in HA Developer Tools → States
# Look for: climate.room_hvac_*

# Debug attributes include:
# - entry_id
# - force_mode
# - ac_entity_id
# - fh_entity_id
# - active_device (AC/FH/None)
```

## Project-Specific Patterns

### File Structure
```
room_hvac/
├── __init__.py          # Entry/unload only (58 lines)
├── climate.py           # Main logic - 345 lines
├── config_flow.py       # 5-step wizard - 466 lines
├── const.py             # All constants (35 lines)
├── manifest.json        # Integration metadata
├── strings.json         # i18n messages (Chinese)
└── translations/
    └── en.json          # English translations
```

### Naming Conventions
- Entity ID format: `climate.room_hvac_{entry_id}`
- Unique ID format: `room_hvac_{entry_id}`
- Config keys: `ac_entity_id`, `fh_entity_id`, `force_mode`, `ac_presets`, `fh_presets`
- Preset slots: `slot_1`, `slot_2`, `slot_3`, `slot_4`
- Preset naming: User-defined names, stored as keys in dict

### Error Handling
- All service calls use `blocking=True`
- Errors are logged and re-raised
- Validation happens in config flow, not at runtime
- No silent failures - all errors logged with context
- Temperature validation: Adjusts to min/max with warnings

### Logging Strategy
- **INFO**: Mode switches, preset activations, successful operations, device routing
- **WARNING**: Capability mismatches, range adjustments, missing attributes
- **ERROR**: Service call failures, validation errors, entity not found
- **DEBUG**: State updates, temperature values, device state changes

### Service Call Patterns
```python
await self.hass.services.async_call(
    "climate",
    "set_hvac_mode",
    {"entity_id": entity_id, "hvac_mode": mode},
    blocking=True,  # Always use blocking
)
```

## Extra State Attributes
The integration provides these debug attributes:
- `entry_id`: The config entry ID
- `force_mode`: Boolean indicating force control mode
- `ac_entity_id`: The AC entity ID
- `fh_entity_id`: The FH entity ID
- `active_device`: "AC", "FH", or None (current active device)

## Integration with Home Assistant
- Follows standard Home Assistant custom component patterns
- Uses `climate` platform with `ClimateEntity` base class
- Supports `TARGET_TEMPERATURE` and `PRESET_MODE` features
- Temperature unit: Celsius (UnitOfTemperature.CELSIUS)
- Target temperature step: 1.0
- IoT Class: local_polling
- Single instance allowed (enforced in config flow)

## Key Constraints
- **Force mode**: Optional, blocks external changes (not fully implemented)
- **Preset slots**: 4 max, empty ones hidden automatically
- **State isolation**: No cross-device contamination
- **Error handling**: All failures logged, no silent errors
- **Mode routing**: Fixed mapping, no flexibility allowed

## Documentation
- `docs/FunctionalSpec.md` - Complete requirements (Chinese)
- `docs/ConfigFlow.md` - Wizard logic (Chinese)
- `docs/AgentTaskMileston.md` - Implementation milestones
- `README.md` - Installation guide (English)

## Current Implementation Status
- ✅ Core routing logic implemented
- ✅ State synchronization working
- ✅ Config flow with 5-step wizard
- ✅ Preset system (AC + FH)
- ✅ Preset activation implemented
- ✅ Temperature range validation
- ✅ Comprehensive error handling
- ⚠️ Force mode (partially implemented - needs state listener for external changes)

## Success Check
All features implemented: routing ✅, presets ✅, validation ✅, state sync ✅, preset activation ✅, error handling ✅