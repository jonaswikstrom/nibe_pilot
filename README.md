# NibePilot

AI-powered control for Nibe heat pumps using Claude API.

NibePilot uses artificial intelligence to optimize your Nibe exhaust air heat pump for comfort and energy efficiency.

## Features

- **AI-Powered Analysis**: Uses Claude API to analyze sensor data and weather forecasts
- **Adaptive Control**: Automatically adjusts heat curve and offset based on conditions
- **Weather Integration**: Uses weather forecasts to predict heating needs
- **Electricity Price Support**: Optional integration with Nordpool for cost optimization
- **Safe Operation**: Conservative limits and confidence thresholds prevent drastic changes
- **Transparent Decisions**: View AI reasoning and recommendations in Home Assistant

## Requirements

- Home Assistant 2024.1.0 or newer
- Nibe heat pump with ESPNibe or similar integration
- Claude API key from Anthropic

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots in the top right corner
3. Select "Custom repositories"
4. Add this repository URL and select "Integration"
5. Search for "NibePilot" and install
6. Restart Home Assistant

### Manual

1. Download this repository
2. Copy `custom_components/nibe_pilot` to your `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "NibePilot"
4. Follow the configuration wizard:
   - Enter your Claude API key
   - Set update interval (5-60 minutes)
   - Select temperature sensors (outdoor, indoor, supply)
   - Select control entities (heat curve, offset)
   - Optionally add weather and electricity price entities

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| `switch.nibe_pilot_auto_mode` | Switch | Enable/disable automatic control |
| `sensor.nibe_pilot_recommendation` | Sensor | Current AI recommendation |
| `sensor.nibe_pilot_analysis` | Sensor | AI analysis and reasoning |
| `sensor.nibe_pilot_confidence` | Sensor | Confidence level (0-100%) |
| `sensor.nibe_pilot_last_action` | Sensor | Last action taken |

## How It Works

1. NibePilot collects data from your configured sensors
2. It fetches weather forecasts and optionally electricity prices
3. All data is sent to Claude API for analysis
4. The AI returns a recommendation with confidence level
5. If auto-mode is enabled and confidence is above threshold, changes are applied
6. All decisions are logged and visible in Home Assistant

## Safety Features

- **Auto-mode disabled by default**: You must explicitly enable automatic control
- **Confidence threshold**: Only recommendations with >70% confidence are applied
- **Limited adjustments**: Heat curve changes limited to +/-5, offset to +/-3
- **Transparent operation**: All AI decisions and reasoning are visible

## Sensor Requirements

### Required Sensors
- Outdoor temperature (BT1)
- Indoor temperature (BT50 or similar)
- Supply/flow temperature (BT2)

### Optional Sensors
- Return temperature (BT3)
- Compressor frequency
- Power consumption
- Hot water temperature (BT6/BT7)

## Control Entities

For automatic control, configure at least one of:
- Heat curve (number or input_number entity)
- Heat offset (number or input_number entity)
- Temperature setpoint (climate or number entity)

## External Data Sources

### Weather Forecast
Any Home Assistant weather integration works. The integration uses the forecast attribute.

### Electricity Price
Supports Nordpool integration. Uses `raw_today` and `raw_tomorrow` attributes for hourly prices.

## Privacy

- Sensor data is sent to Claude API for analysis
- No personal information beyond sensor readings is transmitted
- Claude API has its own privacy policy: https://www.anthropic.com/privacy

## Troubleshooting

### Invalid API Key
Ensure your Claude API key is correct and has sufficient credits.

### No Recommendations
Check that all required sensors are reporting valid values.

### Changes Not Applied
Verify auto-mode is enabled and control entities are configured correctly.

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please submit issues and pull requests on GitHub.
