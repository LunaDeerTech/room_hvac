# Room HVAC Integration - AI Agent Instructions

## Project Overview
This is a Home Assistant custom integration that provides room-level HVAC management by abstracting multiple climate devices (AC + floor heating) into a single unified climate entity. The integration uses smart routing to direct commands to the appropriate device based on HVAC mode.

**Critical**: This project has a complete implementation following strict functional specifications. All major features are implemented and tested.

## Architecture & Key Patterns

### Core Structure
```
custom_components/room_hvac/
├── __init__.py          # Entry point setup, platform forwarding
├── climate.py           # Main entity implementation (705 lines)
├── config_flow.py       # 5-step configuration wizard (466 lines)
├── const.py             # Constants, mode mappings, slot definitions
├── manifest.json        # Integration metadata
├── strings.json         # UI text and error messages
└── translations/        # Localization
```

### Key Design Principles
1. **Single Entity Pattern**: One `RoomHVACClimateEntity` per integration instance
2. **Smart Routing**: Mode → Device mapping (cool/dry/fan_only → AC, heat → FH, off → both)
3. **Dual Preset Systems**: Separate AC (fan speed) and FH (temperature) preset slots
4. **Force Control Mode**: Optional strict enforcement preventing external modifications
5. **State Consistency**: Prevents event loops with internal update tracking

### Critical File Dependencies
- **const.py**: Defines all mode mappings (`AC_HVAC_MODES`, `FH_HVAC_MODES`)
- **climate.py**: Implements routing logic, state listeners, force mode corrections
- **config_flow.py**: Handles entity validation, capability detection, preset configuration

## Development Workflow

### Building & Validation
```bash
# Validate integration structure
cd custom_components/room_hvac
python -m py_compile __init__.py climate.py config_flow.py const.py

# Run Home Assistant validation
# Note: Requires HA environment
hassfest
```

### Testing Patterns
**Must test these specific scenarios:**
1. **Mode Routing**: Verify cool/dry/fan_only → AC, heat → FH, off → all off
2. **Force Mode**: Test external modification detection and immediate correction
3. **Preset Dynamics**: Verify preset list changes with HVAC mode
4. **State Sync**: Test non-force mode allows reverse synchronization
5. **Error Handling**: Test entity validation failures in config flow

### Debugging Commands
```bash
# Monitor integration logs
tail -f home-assistant.log | grep "room_hvac"

# Check entity state
# Developer Tools → States → climate.room_hvac_*
```

## Critical Implementation Details

### Entity Validation Requirements
**Config Flow Step 1** must validate:
- Entities are different (`ac_entity_id != fh_entity_id`)
- Both are climate domain entities
- AC has `fan_modes` attribute and supports cool/dry/fan_only
- FH supports `heat` mode and `target_temperature`
- Entities are available (not `unknown`/`unavailable`)

### State Change Detection
**climate.py** uses sophisticated tracking:
```python
# Internal update detection
_last_internal_update[entity_id] = current_time
if current_time - last_update < 2.0:  # 2-second window
    return  # Ignore our own updates

# Force mode correction
_correction_in_progress[entity_id] = True  # Prevent recursion
```

### Preset Configuration Rules
- **4 slots** per preset type (AC/FH) - configurable but fixed count
- **AC presets**: Map name → fan_mode
- **FH presets**: Map name → temperature (validated against entity min/max)
- **Empty slots**: Automatically filtered in `_build_config_data()`
- **Dynamic display**: `preset_modes` property returns different lists per HVAC mode

### Force Mode Behavior
- **Enabled**: External changes trigger immediate correction via service calls
- **Correction**: Uses `blocking=True` service calls
- **Failure**: Raises exception, no automatic降级
- **Tracking**: Uses `_correction_in_progress` flags to prevent loops

## Project-Specific Conventions

### Naming Conventions
- **Classes**: `RoomHVACClimateEntity`, `RoomHVACConfigFlow`
- **Methods**: `_private_method()` for internal logic
- **Constants**: `DOMAIN`, `AC_HVAC_MODES`, `PRESET_SLOTS`
- **Attributes**: `_attr_` prefix (HA convention)
- **State tracking**: `_last_internal_update`, `_correction_in_progress`

### Error Handling Strategy
- **Config Flow**: Use specific error keys (`"ac_no_fan_modes"`, `"fh_no_heat_mode"`)
- **Runtime**: Log errors with context, then re-raise
- **Force Mode**: No降级, immediate failure on correction errors
- **Logging**: INFO for operations, WARNING for inconsistencies, ERROR for failures

### State Management
- **Temperature Source**: Always from active device (AC or FH)
- **Mode Switching**: Always turns off current device first
- **Preset Application**: Changes parameters without changing HVAC mode
- **No Memory**: Never auto-restore previous settings

## Key Files & Their Roles

### `const.py` - The Source of Truth
- Defines all supported HVAC modes
- Maps modes to device types (AC vs FH)
- Preset slot identifiers
- Configuration key names

### `climate.py` - The Brain
- **State Listeners**: Tracks AC/FH changes via `async_track_state_change_event`
- **Routing Logic**: `async_set_hvac_mode()` with device switching
- **Force Mode**: `_enforce_force_mode_consistency()` + `_correct_inconsistency()`
- **Preset Logic**: `async_set_preset_mode()` with dynamic mode mapping
- **Properties**: `current_temperature`, `preset_modes`, `extra_state_attributes`

### `config_flow.py` - The Gatekeeper
- **5 Steps**: user → behavior → ac_presets → fh_presets → confirm
- **Validation**: Entity existence, capabilities, ranges
- **Preset Collection**: 4 slots with optional configuration
- **Summary**: Builds human-readable confirmation page

## Common Pitfalls to Avoid

1. **Don't change preset slot count**: System expects exactly 4 slots per type
2. **Don't implement auto-restore**: Specs explicitly forbid memory behavior
3. **Don't allow device parallelism**: Always ensure single active device
4. **Don't ignore force mode failures**: Must raise, not降级
5. **Don't change mode mappings**: AC_HVAC_MODES and FH_HVAC_MODES are fixed

## Integration-Specific Patterns

### State Change Event Flow
```
1. External device change detected
2. Check if internal update (2-second window)
3. If force mode enabled:
   - Compare expected vs actual state
   - If mismatch: set correction flag → call service → reset flag
4. If force mode disabled:
   - Sync our state from device (reverse sync)
```

### Configuration Data Structure
```python
{
    "ac_entity_id": "climate.living_room_ac",
    "fh_entity_id": "climate.floor_heating",
    "force_mode": true,
    "ac_presets": {
        "Quiet": {"fan_mode": "low", "icon": "mdi:weather-night"},
        "Turbo": {"fan_mode": "high", "icon": "mdi:weather-windy"}
    },
    "fh_presets": {
        "Home": {"temperature": "21", "icon": "mdi:home"}
    }
}
```

### Entity Attributes (Debugging)
```python
{
    "entry_id": "abc123",
    "force_mode": true,
    "ac_entity_id": "climate.living_room_ac",
    "fh_entity_id": "climate.floor_heating",
    "active_device": "AC",  # or "FH" or None
    "ac_correcting": false,  # debugging flag
    "fh_correcting": false,  # debugging flag
    "listener_count": 2
}
```

## Testing Checklist

Before making changes, verify these work:
- [ ] Config flow accepts valid AC/FH entities
- [ ] Config flow rejects invalid entities with clear errors
- [ ] 5-step configuration completes successfully
- [ ] Entity appears in HA UI after configuration
- [ ] Mode routing works (all 5 modes)
- [ ] Temperature control works in cool/dry/heat modes
- [ ] Preset lists change dynamically with mode
- [ ] Preset activation applies correct parameters
- [ ] Force mode detects external changes
- [ ] Force mode corrects inconsistencies
- [ ] State listeners don't cause event loops
- [ ] Error handling shows meaningful messages

## Version Information
- Current Version: 0.1.0
- Minimum HA Version: 2024.1.0
- Integration Type: local_polling
- Config Flow: Yes (5 steps)
- Platforms: climate only

## Related Documentation
- `docs/FunctionalSpec.md` - Complete functional requirements
- `docs/ConfigFlow.md` - Configuration flow details
- `docs/AgentTaskMileston.md` - Development milestones
- `docs/SelfCheckReport.md` - Pre-release validation report
- `README.md` - User-facing installation and usage guide

## Critical Success Factors

1. **Follow the Specs**: This implementation is complete and tested. Don't deviate from documented behavior.
2. **Respect the Architecture**: The 5-file structure is intentional and complete.
3. **Maintain State Consistency**: The event tracking and force mode logic are sophisticated - preserve them.
4. **Keep Validation Strict**: Config flow validation prevents user errors - keep it comprehensive.
5. **Log Verbosely**: The integration has excellent debug logging - maintain this standard.

When working on this codebase, always reference the existing implementation patterns before making changes. The project follows Home Assistant best practices and has been thoroughly validated.