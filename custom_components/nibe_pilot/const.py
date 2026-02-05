from typing import Final

DOMAIN: Final = "nibe_pilot"
PLATFORMS: Final = ["sensor", "select", "button"]

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
CONF_MANUAL_SETPOINT: Final = "manual_setpoint"
CONF_WEATHER: Final = "weather_entity"
CONF_ELECTRICITY_PRICE: Final = "electricity_price_entity"

CONF_MAX_HEAT_CURVE_DELTA: Final = "max_heat_curve_delta"
CONF_MAX_HEAT_OFFSET_DELTA: Final = "max_heat_offset_delta"
CONF_CONFIDENCE_THRESHOLD: Final = "confidence_threshold"
CONF_MIN_INDOOR_TEMP: Final = "min_indoor_temp"
CONF_MAX_INDOOR_TEMP: Final = "max_indoor_temp"
CONF_COOLDOWN_MINUTES: Final = "cooldown_minutes"
CONF_BUILDING_TYPE: Final = "building_type"
CONF_NOTIFY_SERVICE: Final = "notify_service"
CONF_CONTROL_MODE: Final = "control_mode"

CONTROL_MODE_MANUAL: Final = "manual"
CONTROL_MODE_NOTIFY: Final = "notify"
CONTROL_MODE_AUTO: Final = "auto"

EVENT_NOTIFICATION_RESPONSE: Final = "nibe_pilot_notification_response"
NOTIFICATION_TAG: Final = "nibe_pilot_recommendation"

DEFAULT_UPDATE_INTERVAL: Final = 15
DEFAULT_CONFIDENCE_THRESHOLD: Final = 0.7
DEFAULT_MAX_HEAT_CURVE_DELTA: Final = 5
DEFAULT_MAX_HEAT_OFFSET_DELTA: Final = 3
DEFAULT_MIN_INDOOR_TEMP: Final = 18.0
DEFAULT_MAX_INDOOR_TEMP: Final = 24.0
DEFAULT_COOLDOWN_MINUTES: Final = 30

ATTR_RECOMMENDATION: Final = "recommendation"
ATTR_REASONING: Final = "reasoning"
ATTR_CONFIDENCE: Final = "confidence"
ATTR_LAST_ACTION: Final = "last_action"
ATTR_LAST_UPDATE: Final = "last_update"
ATTR_AUTO_MODE: Final = "auto_mode"

MAX_HEAT_CURVE_DELTA: Final = 5
MAX_HEAT_OFFSET_DELTA: Final = 3

CLAUDE_MODEL: Final = "claude-sonnet-4-5-20250929"
