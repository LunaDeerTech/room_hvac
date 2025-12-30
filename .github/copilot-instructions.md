# Copilot Instructions for room_hvac Integration

## Project Overview

**room_hvac** is a Home Assistant custom integration that provides room-level HVAC management by abstracting multiple climate devices (air conditioner + floor heating) into a single, unified climate entity. This is a **specification-driven** project currently in implementation phase.

### Core Architecture Pattern

The integration follows a **router/mediator pattern** where:
- **Single entry point**: One `climate` entity exposed to Home Assistant
- **Dual execution devices**: Routes commands to either AC or floor heating based on mode
- **Mode arbitration**: Only one downstream device active at any time
- **Preset abstraction**: Two independent preset systems (AC fan speeds, heating temperatures)

## Critical Implementation Files (Priority Order)

1. **`manifest.json`** - Integration metadata
2. **`__init__.py`** - Setup entry point  
3. **`const.py`** - All constants and enums
4. **`config_flow.py`** - Configuration wizard with validation
5. **`climate.py`** - Main RoomHVACClimateEntity implementation

## Key Design Constraints

### HVAC Mode Routing (Non-negotiable)
```python
#空调类模式 → 空调设备
COOL_MODES = {"cool", "dry", "fan_only"}
#制热模式 → 地暖设备  
HEAT_MODES = {"heat"}
#关闭模式 → 所有设备关闭
```

### Device State Management
- **Never** allow AC and floor heating to be active simultaneously
- Mode switches **must** force-off the inactive device
- `current_temperature` always reflects the **active** device's sensor

### Preset System Dynamics
- **AC Presets**: Map to `fan_mode` values (cool/dry/fan_only modes)
- **Heating Presets**: Map to target temperatures (heat mode only)
- **Dynamic visibility**: Preset list changes based on current HVAC mode
- **4 slots maximum**: User-configurable names/icons, empty slots hidden

### Force Control Mode (Optional Feature)
- Prevents external changes to the unified entity
- Ensures control consistency in multi-user environments
- Must be explicitly enabled in config flow

## Configuration Flow Requirements

### Step-by-Step Wizard (No Single Form)
1. **Device Selection**: Choose AC + floor heating entities (distinct)
2. **Capability Validation**: Verify devices support required features
3. **Behavior Options**: Force mode toggle, basic settings
4. **AC Preset Config**: 4 slots for fan modes
5. **Heating Preset Config**: 4 slots for temperatures
6. **Confirmation**: Review & create

### Critical Validations
- Entity domains must be `climate`
- Entities must be distinct
- Devices must be available during setup
- AC must support fan modes; Heating must support temperature

## Development Patterns

### State Consistency
- **Always** derive `current_temperature` from active device
- **Never** cache temperature across mode switches
- **Always** update `hvac_action` based on active device state

### Error Handling
- **Fail fast** during config flow with clear error messages
- **Graceful degradation**: If preset slot empty, hide from UI
- **No silent failures**: All mode/routing errors must log

### Preset Implementation Pattern
```python
# Dynamic preset_modes property
@property
def preset_modes(self):
    if self.hvac_mode in COOL_MODES:
        return [name for name, mode in self._ac_presets.items() if mode]
    elif self.hvac_mode in HEAT_MODES:
        return [name for name, mode in self._heat_presets.items() if mode]
    return []
```

## Testing Strategy (Spec-Driven)

Since this is spec-driven development, tests must validate:
1. **Routing correctness**: Mode → Device mapping
2. **State isolation**: No cross-contamination between modes
3. **Preset dynamics**: Correct presets shown per mode
4. **Config validation**: All edge cases in wizard
5. **Force mode behavior**: External change prevention

## External Dependencies

- **Home Assistant Core**: Climate entity base classes
- **Entity Registry**: Device discovery and validation
- **State Machine**: Device state monitoring
- **Config Entry**: Persistent storage setup

## Project-Specific Conventions

### Naming
- **Chinese-first**: Primary docs in Chinese (use existing specs)
- **English code**: All code/comments in English
- **Descriptive**: Constants like `SUPPORT_AC_FAN_MODES` not magic values

### File Structure
- **Single responsibility**: One file per major component
- **Flat structure**: No subdirectories in integration root
- **Const centralization**: All enums in `const.py`

### Error Messages
- **User-facing**: Config flow errors in Chinese
- **Developer-facing**: Logs in English with context
- **Actionable**: Always suggest resolution

## Implementation Milestones (Current Status)

**You are here**: Milestone 0 - Specification complete, ready to start implementation

**Next steps**:
1. Create minimal integration structure
2. Implement basic entity registration
3. Build config flow with validation
4. Implement routing logic
5. Add preset systems
6. Test all mode transitions

## Key Files to Reference

- `docs/FunctionalSpec.md` - Complete functional requirements
- `docs/ConfigFlow.md` - Detailed config flow logic
- `docs/AgentTaskMileston.md` - Step-by-step implementation guide

## Common Pitfalls to Avoid

1. **Don't** implement bidirectional state sync (unidirectional routing only)
2. **Don't** add new HVAC modes beyond the 5 specified
3. **Don't** cache temperature values across mode switches
4. **Don't** show empty preset slots
5. **Don't** skip validation in config flow

## Success Criteria

The integration is complete when:
- ✅ Single climate entity appears in HA
- ✅ All 5 modes route to correct devices
- ✅ Presets show/hide dynamically
- ✅ Config flow validates all constraints
- ✅ Force mode prevents external changes (if enabled)
- ✅ No simultaneous device activation