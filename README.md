# Room HVAC Integration

A Home Assistant custom integration that provides room-level HVAC management by abstracting multiple climate devices (air conditioner + floor heating) into a single, unified climate entity.

## Overview

This integration creates a single climate entity that routes commands to either AC or floor heating based on the selected mode, providing a unified control interface for room climate management.

## Features

- **Single Entry Point**: One climate entity for the entire room
- **Smart Routing**: Automatically routes to AC or floor heating based on mode
- **Dual Preset Systems**: Separate presets for AC fan speeds and heating temperatures
- **Force Control Mode**: Optional mode to prevent external changes
- **Dynamic Presets**: Preset list changes based on current HVAC mode

## Installation

1. Copy the `room_hvac` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Configuration -> Integrations -> Add Integration -> Search for "Room HVAC"

## Configuration

The integration will guide you through a step-by-step configuration process:

1. **Device Selection**: Choose your AC and floor heating entities
2. **Behavior Options**: Configure force control mode
3. **AC Presets**: Set up fan speed presets (4 slots available)
4. **Heating Presets**: Set up temperature presets (4 slots available)
5. **Confirmation**: Review and create the integration

## Supported Modes

- `off` - All devices off
- `cool` - Routes to AC
- `dry` - Routes to AC
- `fan_only` - Routes to AC
- `heat` - Routes to floor heating

## Requirements

- Home Assistant 2024.1.0 or later
- A climate entity for air conditioning (supporting fan modes)
- A climate entity for floor heating (supporting temperature control)

## License

MIT License