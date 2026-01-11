# MantelMount MM860 Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/midibach/ha-mantelmount-mm860.svg)](https://github.com/midibach/ha-mantelmount-mm860/releases)
[![License](https://img.shields.io/github/license/midibach/ha-mantelmount-mm860.svg)](LICENSE)

Home Assistant integration for the MantelMount MM860 motorized TV mount with network control capability.

## Features

- **Position Presets**: Select from Home, M1, M2, M3, M4 presets via dropdown
- **Smart Preset Learning**: Automatically learns preset positions when recalled
- **Jog Controls**: Manual movement buttons (Up, Down, Left, Right, Stop)
- **Position Sensors**: Real-time elevation and azimuth readings
- **Temperature Monitoring**: Internal temperature sensor (displays in your preferred units)
- **Movement Detection**: Binary sensor shows when mount is moving
- **Save Presets**: Buttons to save current position to M1-M4
- **Diagnostic Sensors**: Actuator positions, motor currents, firmware version

## Requirements

- MantelMount MM860 with network adapter connected and reachable on the same network as Home Assistant
- Mount must be accessible via UDP on port 81. If you are not filtering network traffic, this is not a concern.

> **⚠️ Important Notes:**
> - This integration has **not been tested on the MM860 v2**
> - The M3 and M4 presets are not exposed on the RF remote, but the mount does store and retrieve them via this integration
> - No warranty or support of any kind is provided
> - **Use at your own risk**

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots in the top right corner
3. Select "Custom repositories"
4. Add this repository URL: `https://github.com/midibach/ha-mantelmount-mm860`
5. Select category: "Integration"
6. Click "Add"
7. Search for "MantelMount" and install
8. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Extract and copy the `custom_components/mantelmount_mm860` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "MantelMount MM860"
4. Enter your mount's IP address
5. Configure options:
   - **Poll interval**: How often to query status (default: 0.1s / 100ms). This matches the interval used by the Windows utility. You may want to increase this to conserve HA compute resources.
   - **Timeout**: Connection timeout in seconds
   - **Lock while moving**: Prevent new commands while mount is moving. Stop still works.

## Entities

### Controls
| Entity | Type | Description |
|--------|------|-------------|
| Position | Select | Dropdown to recall Home/M1/M2/M3/M4 presets |
| Stop | Button | Stop all movement |
| Jog Up/Down/Left/Right | Button | Manual movement controls |
| Save preset 1-4 | Button | Save current position to preset |

### Sensors
| Entity | Type | Description |
|--------|------|-------------|
| Elevation | Sensor | Current vertical position |
| Azimuth | Sensor | Current horizontal/swivel position |
| Temperature | Sensor | Internal temperature (displays in °F or °C based on your HA settings) |
| Moving | Binary Sensor | On when mount is in motion |

### Diagnostic Sensors
| Entity | Description |
|--------|-------------|
| Left/Right Actuator | Raw actuator positions |
| Left/Right Motor Current | Motor current draw |
| TV Current | TV power sensing |
| Firmware Version | Controller firmware |
| Last Preset | Last recalled preset number |
| Left/Right at Limit | Limit switch status |
| Lost Flag | Position lost indicator |

## Smart Preset Learning

The integration automatically learns preset positions:

1. When you select a preset from the dropdown, the mount moves
2. When movement stops, the current position is saved in HA for that preset to enable accurate state reporting
3. The dropdown then shows which preset matches your current position
4. If you jog away from a preset, the dropdown shows blank

Check the Position entity's attributes to see:
- `learned_presets`: Which presets have been learned
- `current_elevation` / `current_azimuth`: Current position
- `Home_elevation`, `M1_elevation`, etc.: Stored preset positions

Learned positions are persisted across Home Assistant restarts.

## Services

### `mantelmount_mm860.send_command`

Send raw commands to the mount controller.

| Field | Description |
|-------|-------------|
| `command` | ASCII command string (e.g., `MMR1`, `MMQ`) |
| `crlf` | Use CRLF line ending (default: false, uses CR only) |
| `read_reply` | Wait for and return response (default: true) |

## Troubleshooting

### Mount not responding
- Verify the IP address is correct
- Ensure UDP port 81 is accessible
- Check that no firewall is blocking UDP traffic

### Position not updating
- Reduce poll interval (try 0.1s)
- Check the Moving binary sensor during movement

### Preset dropdown not working
- The integration learns positions dynamically
- Recall each preset once to teach the integration their positions

## Protocol Notes

This integration communicates via UDP on port 81 using MantelMount's proprietary protocol:
- `MMQ` - Query status (returns 16-field CSV)
- `MMR0-4` - Recall preset (Home, M1-M4)
- `MMS1-4` - Save preset
- `MMJ0-4` - Jog (0=Stop, 1=Right, 2=Up, 3=Left, 4=Down)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This integration is not affiliated with or endorsed by MantelMount. 

**No warranty or support of any kind is provided. Use at your own risk.**

This software is provided "as is" without any guarantees. The authors are not responsible for any damage to your equipment, property, or persons that may result from using this integration.
