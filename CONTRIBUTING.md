# Contributing to Room HVAC Integration

We welcome contributions to the Room HVAC Integration! 

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a new branch for your feature/fix
4. Make your changes
5. Test thoroughly in your Home Assistant environment
6. Submit a pull request

## Development Setup

The integration follows standard Home Assistant custom component structure:

```
custom_components/room_hvac/
├── __init__.py
├── climate.py
├── config_flow.py
├── const.py
├── manifest.json
├── strings.json
└── translations/
    └── en.json
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Keep functions focused and well-documented
- Use Home Assistant's logging system

## Testing

Before submitting a PR:
1. Test all HVAC modes (cool, dry, fan_only, heat, off)
2. Test preset activation for both AC and floor heating
3. Test configuration flow with various entity combinations
4. Verify error handling works correctly

## Pull Request Process

1. Update the README.md with details of changes if needed
2. Update version number in manifest.json following semantic versioning
3. Ensure all tests pass
4. Reference any related issues in your PR description

## Reporting Issues

When reporting issues, please include:
- Home Assistant version
- Integration version
- Relevant logs from `home-assistant.log`
- Steps to reproduce the issue
- Expected vs actual behavior

## Feature Requests

We welcome feature requests! Please open an issue and describe:
- The problem you're trying to solve
- Proposed solution
- Alternative solutions you've considered