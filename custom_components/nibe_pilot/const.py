from typing import Final

DOMAIN: Final = "nibe_pilot"
PLATFORMS: Final = ["sensor", "switch"]

CONF_API_KEY: Final = "api_key"
CONF_UPDATE_INTERVAL: Final = "update_interval"
CONF_OUTDOOR_TEMP: Final = "outdoor_temp_entity"
CONF_INDOOR_TEMP: Final = "indoor_temp_entity"
CONF_SUPPLY_TEMP: Final = "supply_temp_entity"
CONF_COMPRESSOR_FREQ: Final = "compressor_freq_entity"
CONF_POWER_CONSUMPTION: Final = "power_consumption_entity"
CONF_HOT_WATER_TEMP: Final = "hot_water_temp_entity"
CONF_RETURN_TEMP: Final = "return_temp_entity"
CONF_HEAT_CURVE: Final = "heat_curve_entity"
CONF_HEAT_OFFSET: Final = "heat_offset_entity"
CONF_SETPOINT: Final = "setpoint_entity"
CONF_WEATHER: Final = "weather_entity"
CONF_ELECTRICITY_PRICE: Final = "electricity_price_entity"

DEFAULT_UPDATE_INTERVAL: Final = 15
DEFAULT_CONFIDENCE_THRESHOLD: Final = 0.7

ATTR_RECOMMENDATION: Final = "recommendation"
ATTR_REASONING: Final = "reasoning"
ATTR_CONFIDENCE: Final = "confidence"
ATTR_LAST_ACTION: Final = "last_action"
ATTR_LAST_UPDATE: Final = "last_update"
ATTR_AUTO_MODE: Final = "auto_mode"

MAX_HEAT_CURVE_DELTA: Final = 5
MAX_HEAT_OFFSET_DELTA: Final = 3

CLAUDE_MODEL: Final = "claude-sonnet-4-20250514"
