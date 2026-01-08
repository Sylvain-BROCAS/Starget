# Starget - AI Coding Agent Instructions

## Project Overview
Starget is a telescope mount controller project based on OnStepX firmware.

**Goal**: Ultra-portable equatorial mount for DSLR telescopes controlled via ASCOM standard.

**Hardware Target**: Simple OnStep implementation with:
- 1× ESP32 DevKit V1
- 2× Stepper motors with TMC2209 drivers (RA + Dec axes)
- USB serial communication (no WiFi/Bluetooth)
- Custom pinmap configuration

**Control**: Uses official OnStep ASCOM driver (not the experimental Python code in `device/`)

## Architecture

### Firmware Stack (ESP32/Arduino) - ACTIVE
- **Active Project**: `260103-160031-upesy_wroom/` PlatformIO workspace
- **Source**: Soft-linked from `remake/OnStepX-custom/` (Howard Dutton's OnStepX controller)
- **Configuration**: [Config.h](remake/OnStepX-custom/Config.h) + [Extended.config.h](remake/OnStepX-custom/Extended.config.h) - Stepper drivers, pinmaps, axis limits
- **Build System**: PlatformIO with `upesy_wroom` board target
- **Pinmap**: Custom hardware configuration (`PINMAP CUSTOM` in Config.h) - see pinmaps/Pins.Custom.h for GPIO assignments
- **Drivers**: TMC2209 STEP/DIR mode for both axes (UART configuration available but uses simple step/direction control)

### Python Alpaca Driver (device/) - EXPERIMENTAL/UNUSED
The `device/` directory contains an experimental Alpaca REST API implementation that is NOT currently used. The project uses the official OnStep ASCOM driver instead. This code may be useful for reference or future Alpaca migration but is not part of the active system.

## Critical Workflows

### Building/Uploading Firmware
```bash
# From PlatformIO workspace root
pio run                    # Build only
pio run --target upload    # Upload to ESP32
```
**Common Issue**: Upload failures (exit code 1) often indicate COM port conflicts or cable issues. Check PlatformIO terminal for specific errors.

### Connecting via ASCOM Driver
1. Upload firmware to ESP32 via PlatformIO
2. Connect ESP32 to Windows PC via USB
3. Use official OnStep ASCOM driver to connect to COM port
4. Control from ASCOM-compatible software (NINA, etc.)

## Project-Specific Conventions

### Configuration Management
- **NEVER hardcode firmware values** - All OnStepX parameters live in [Config.h](remake/OnStepX-custom/Config.h) and [Extended.config.h](remake/OnStepX-custom/Extended.config.h)
- Key settings: AXIS1/2_STEPS_PER_DEGREE, AXIS1/2_DRIVER_MODEL, PINMAP
- OnStepX uses `#define` directives - changes require firmware recompilation

## External Dependencies
- **Firmware**: OnStepX libraries (axis control, TMC stepper drivers, LX200 protocol)
- **ASCOM Driver**: Official OnStep ASCOM driver for Windows control
- **Hardware Docs**: TMC2209 datasheet, ESP32 DevKit V1 pinout

## File Organization Anti-Patterns
- **Avoid**: `old/` contains deprecated rotator code - do not reference
- **Multiple OnStepX versions**: `remake/OnStepX-{custom,original,waerhert}` - Only `-custom` is active
- **Unused**: `device/` folder contains experimental Python Alpaca driver not used in production
- **Unused**: `templates/` has Alpaca JSON schemas - ignore, using official OnStep ASCOM driver

## Testing & Validation
- **No automated tests** - Manual validation workflow
- Test with official OnStep ASCOM driver via USB serial connection
- Firmware validation: Monitor serial output during operation
- Deployment: USB serial connection for both firmware upload (PlatformIO) and runtime control (ASCOM driver)
- Motor serial: [motor_control.py](device/motor_control.py) contains encoder calibration sequences
- Coordinate math: Import [utilities.py](device/utilities.py) functions directly for manual testing
- Deployment: USB serial connection for both firmware upload (PlatformIO) and runtime control (Python driver)s
- Coordinate math: Import [utilities.py](device/utilities.py) functions directly for unit testing

## Known Quirks
- Config.h comments: OnStepX uses inline HTML-style comments - preserve formatting when editing
- Upload failures (exit code 1): Usually COM port conflicts or cable issues - check PlatformIO terminal output
- Custom pinmap: GPIO assignments in Pins.Custom.h must match physical wiring
