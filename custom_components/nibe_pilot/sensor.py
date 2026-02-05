import logging
from datetime import datetime
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ATTR_CONFIDENCE
from .coordinator import NibePilotCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NibePilotCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        NibePilotRecommendationSensor(coordinator, entry),
        NibePilotAnalysisSensor(coordinator, entry),
        NibePilotConfidenceSensor(coordinator, entry),
        NibePilotLastActionSensor(coordinator, entry),
        NibePilotTokenUsageSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class NibePilotBaseSensor(CoordinatorEntity[NibePilotCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NibePilotCoordinator,
        entry: ConfigEntry,
        key: str,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "NibePilot",
            "manufacturer": "Community",
            "model": "AI Heat Pump Controller",
            "sw_version": "1.0.4",
        }


class NibePilotRecommendationSensor(NibePilotBaseSensor):
    _attr_name = "Rekommendation"
    _attr_icon = "mdi:head-lightbulb"

    def __init__(self, coordinator: NibePilotCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry, "recommendation")

    @property
    def native_value(self) -> str:
        if not self.coordinator.data:
            return "Väntar på data"

        recommendation = self.coordinator.data.get("recommendation", {})
        action = recommendation.get("action", "unknown")

        action_texts = {
            "no_change": "Ingen ändring",
            "adjust_heat_curve": "Justera värmekurva",
            "adjust_offset": "Justera värmeoffset",
        }

        return action_texts.get(action, action)

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}

        recommendation = self.coordinator.data.get("recommendation", {})
        return {
            "heat_curve_delta": recommendation.get("heat_curve_delta", 0),
            "heat_offset_delta": recommendation.get("heat_offset_delta", 0),
            ATTR_CONFIDENCE: recommendation.get("confidence", 0),
            "last_update": datetime.now().isoformat(),
        }


class NibePilotAnalysisSensor(NibePilotBaseSensor):
    _attr_name = "AI-analys"
    _attr_icon = "mdi:robot"

    def __init__(self, coordinator: NibePilotCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry, "analysis")

    @property
    def native_value(self) -> str:
        if not self.coordinator.data:
            return "Väntar på analys"

        recommendation = self.coordinator.data.get("recommendation", {})
        reasoning = recommendation.get("reasoning", "Ingen analys tillgänglig")

        if len(reasoning) > 255:
            return reasoning[:252] + "..."
        return reasoning

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}

        recommendation = self.coordinator.data.get("recommendation", {})
        sensor_data = self.coordinator.data.get("sensor_data", {})

        return {
            "full_reasoning": recommendation.get("reasoning", ""),
            "action": recommendation.get("action", ""),
            ATTR_CONFIDENCE: recommendation.get("confidence", 0),
            "outdoor_temp": sensor_data.get("outdoor_temp"),
            "indoor_temp": sensor_data.get("indoor_temp"),
            "supply_temp": sensor_data.get("supply_temp"),
            "heat_curve": sensor_data.get("heat_curve"),
            "heat_offset": sensor_data.get("heat_offset"),
            "auto_mode": self.coordinator.auto_mode,
        }


class NibePilotConfidenceSensor(NibePilotBaseSensor):
    _attr_name = "AI-confidence"
    _attr_icon = "mdi:percent"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: NibePilotCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry, "confidence")

    @property
    def native_value(self) -> float:
        if not self.coordinator.data:
            return 0

        recommendation = self.coordinator.data.get("recommendation", {})
        confidence = recommendation.get("confidence", 0)
        return round(confidence * 100, 1)


class NibePilotLastActionSensor(NibePilotBaseSensor):
    _attr_name = "Senaste åtgärd"
    _attr_icon = "mdi:history"

    def __init__(self, coordinator: NibePilotCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry, "last_action")

    @property
    def native_value(self) -> str:
        if not self.coordinator.data:
            return "Ingen åtgärd"

        return self.coordinator.data.get("last_action", "Ingen åtgärd")

    @property
    def extra_state_attributes(self):
        details = self.coordinator.control_service.last_action_details
        return {
            "reason": details.get("reason", ""),
            ATTR_CONFIDENCE: details.get("confidence"),
            "delta": details.get("delta"),
            "timestamp": datetime.now().isoformat(),
        }


class NibePilotTokenUsageSensor(NibePilotBaseSensor):
    _attr_name = "Token-förbrukning"
    _attr_icon = "mdi:counter"
    _attr_native_unit_of_measurement = "tokens"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: NibePilotCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry, "token_usage")

    @property
    def native_value(self) -> int:
        stats = self.coordinator.claude_service.token_stats
        return stats.get("total_tokens", 0)

    @property
    def extra_state_attributes(self):
        stats = self.coordinator.claude_service.token_stats
        return {
            "total_input_tokens": stats.get("total_input_tokens", 0),
            "total_output_tokens": stats.get("total_output_tokens", 0),
            "last_input_tokens": stats.get("last_input_tokens", 0),
            "last_output_tokens": stats.get("last_output_tokens", 0),
            "last_tokens": stats.get("last_tokens", 0),
            "api_calls_count": stats.get("api_calls_count", 0),
            "api_available": self.coordinator.claude_service.api_available,
            "last_error": self.coordinator.claude_service.last_error,
        }
