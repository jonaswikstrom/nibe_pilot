import logging
from datetime import timedelta
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_UPDATE_INTERVAL,
    CONF_OUTDOOR_TEMP,
    CONF_INDOOR_TEMP,
    CONF_SUPPLY_TEMP,
    CONF_RETURN_TEMP,
    CONF_COMPRESSOR_FREQ,
    CONF_POWER_CONSUMPTION,
    CONF_HOT_WATER_TEMP,
    CONF_HEAT_CURVE,
    CONF_HEAT_OFFSET,
    CONF_SETPOINT,
    CONF_MANUAL_SETPOINT,
    CONF_WEATHER,
    CONF_ELECTRICITY_PRICE,
    CONF_BUILDING_TYPE,
    DEFAULT_UPDATE_INTERVAL,
)
from .claude_service import ClaudeService
from .control_service import ControlService

_LOGGER = logging.getLogger(__name__)


class NibePilotCoordinator(DataUpdateCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        claude_service: ClaudeService,
        control_service: ControlService,
    ):
        self.entry = entry
        self.claude_service = claude_service
        self.control_service = control_service
        self.auto_mode = False
        self._last_recommendation: dict[str, Any] = {}

        config = {**entry.data, **entry.options}
        update_interval = config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            sensor_data = self._collect_sensor_data()

            if self.control_service.last_action:
                sensor_data["last_action"] = {
                    "action": self.control_service.last_action,
                    **self.control_service.last_action_details,
                }

            _LOGGER.debug("Collected sensor data: %s", sensor_data)

            recommendation = await self.claude_service.get_recommendation(sensor_data)
            self._last_recommendation = recommendation

            _LOGGER.info(
                "AI recommendation: %s (confidence: %.0f%%)",
                recommendation.get("action"),
                recommendation.get("confidence", 0) * 100
            )

            await self.control_service.apply_recommendation(
                recommendation,
                self.auto_mode
            )

            return {
                "sensor_data": sensor_data,
                "recommendation": recommendation,
                "last_action": self.control_service.get_last_action_summary(),
                "auto_mode": self.auto_mode,
            }

        except Exception as err:
            _LOGGER.error("Error during update: %s", err)
            raise UpdateFailed(f"Update failed: {err}") from err

    def _collect_sensor_data(self) -> dict[str, Any]:
        data = {}
        config = {**self.entry.data, **self.entry.options}

        sensor_mappings = {
            "outdoor_temp": CONF_OUTDOOR_TEMP,
            "indoor_temp": CONF_INDOOR_TEMP,
            "supply_temp": CONF_SUPPLY_TEMP,
            "return_temp": CONF_RETURN_TEMP,
            "compressor_freq": CONF_COMPRESSOR_FREQ,
            "power_consumption": CONF_POWER_CONSUMPTION,
            "hot_water_temp": CONF_HOT_WATER_TEMP,
            "heat_curve": CONF_HEAT_CURVE,
            "heat_offset": CONF_HEAT_OFFSET,
            "setpoint": CONF_SETPOINT,
        }

        for data_key, config_key in sensor_mappings.items():
            entity_id = config.get(config_key)
            if entity_id:
                value = self._get_entity_value(entity_id)
                if value is not None:
                    data[data_key] = value

        if "setpoint" not in data and config.get(CONF_MANUAL_SETPOINT):
            data["setpoint"] = config.get(CONF_MANUAL_SETPOINT)

        weather_entity = config.get(CONF_WEATHER)
        if weather_entity:
            data["weather_forecast"] = self._get_weather_forecast(weather_entity)

        price_entity = config.get(CONF_ELECTRICITY_PRICE)
        if price_entity:
            data["electricity_prices"] = self._get_electricity_prices(price_entity)

        if config.get(CONF_BUILDING_TYPE):
            data["building_type"] = config.get(CONF_BUILDING_TYPE)

        return data

    def _get_entity_value(self, entity_id: str) -> float | None:
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return None

        try:
            return float(state.state)
        except (ValueError, TypeError):
            _LOGGER.debug("Cannot parse value from %s: %s", entity_id, state.state)
            return None

    def _get_weather_forecast(self, entity_id: str) -> list[dict[str, Any]]:
        state = self.hass.states.get(entity_id)
        if state is None:
            return []

        forecast = state.attributes.get("forecast", [])
        if not forecast:
            return []

        result = []
        for entry in forecast[:24]:
            result.append({
                "datetime": entry.get("datetime", ""),
                "temperature": entry.get("temperature"),
                "condition": entry.get("condition", ""),
            })

        return result

    def _get_electricity_prices(self, entity_id: str) -> list[dict[str, Any]]:
        state = self.hass.states.get(entity_id)
        if state is None:
            return []

        raw_today = state.attributes.get("raw_today", [])
        raw_tomorrow = state.attributes.get("raw_tomorrow", [])

        result = []
        for entry in raw_today + raw_tomorrow:
            if isinstance(entry, dict):
                result.append({
                    "hour": entry.get("start", ""),
                    "price": entry.get("value"),
                })

        return result[:24]

    @property
    def last_recommendation(self) -> dict[str, Any]:
        return self._last_recommendation

    def set_auto_mode(self, enabled: bool):
        self.auto_mode = enabled
        _LOGGER.info("Auto mode %s", "enabled" if enabled else "disabled")
