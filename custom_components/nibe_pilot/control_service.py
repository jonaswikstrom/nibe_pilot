import logging
from datetime import datetime, timedelta
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.const import ATTR_ENTITY_ID

from .const import (
    CONF_HEAT_CURVE,
    CONF_HEAT_OFFSET,
    CONF_CONFIDENCE_THRESHOLD,
    CONF_COOLDOWN_MINUTES,
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_COOLDOWN_MINUTES,
)

_LOGGER = logging.getLogger(__name__)


class ControlService:
    def __init__(self, hass: HomeAssistant, config: dict[str, Any]):
        self.hass = hass
        self.config = config
        self.last_action: str | None = None
        self.last_action_details: dict[str, Any] = {}
        self.last_adjustment_time: datetime | None = None

    def update_config(self, config: dict[str, Any]):
        self.config = config

    async def apply_recommendation(
        self,
        recommendation: dict[str, Any],
        auto_mode: bool
    ) -> bool:
        if not auto_mode:
            _LOGGER.debug("Auto mode disabled, not applying changes")
            self.last_action = "skipped_manual_mode"
            self.last_action_details = {"reason": "Auto-mode är avaktiverat"}
            return False

        cooldown_minutes = self.config.get(CONF_COOLDOWN_MINUTES, DEFAULT_COOLDOWN_MINUTES)
        if cooldown_minutes > 0 and self.last_adjustment_time:
            time_since_last = datetime.now() - self.last_adjustment_time
            if time_since_last < timedelta(minutes=cooldown_minutes):
                remaining = cooldown_minutes - (time_since_last.total_seconds() / 60)
                _LOGGER.debug("Cooldown active, %.0f minutes remaining", remaining)
                self.last_action = "skipped_cooldown"
                self.last_action_details = {
                    "reason": f"Väntar {remaining:.0f} min (cooldown)",
                }
                return False

        confidence = recommendation.get("confidence", 0)
        confidence_threshold = self.config.get(CONF_CONFIDENCE_THRESHOLD, DEFAULT_CONFIDENCE_THRESHOLD)
        if confidence < confidence_threshold:
            _LOGGER.debug(
                "Confidence %.2f below threshold %.2f, not applying",
                confidence,
                confidence_threshold
            )
            self.last_action = "skipped_low_confidence"
            self.last_action_details = {
                "reason": f"Confidence {confidence:.0%} under tröskelvärde ({confidence_threshold:.0%})",
                "confidence": confidence,
            }
            return False

        action = recommendation.get("action", "no_change")

        if action == "no_change":
            self.last_action = "no_change"
            self.last_action_details = {
                "reason": recommendation.get("reasoning", "Ingen ändring behövs"),
                "confidence": confidence,
            }
            return True

        applied = False

        if action == "adjust_heat_curve":
            delta = recommendation.get("heat_curve_delta", 0)
            if delta != 0:
                applied = await self._adjust_heat_curve(delta)

        elif action == "adjust_offset":
            delta = recommendation.get("heat_offset_delta", 0)
            if delta != 0:
                applied = await self._adjust_heat_offset(delta)

        if applied:
            self.last_action = action
            self.last_action_details = {
                "reason": recommendation.get("reasoning", ""),
                "confidence": confidence,
                "delta": recommendation.get(
                    "heat_curve_delta" if action == "adjust_heat_curve" else "heat_offset_delta",
                    0
                ),
            }
            self.last_adjustment_time = datetime.now()

        return applied

    async def _adjust_heat_curve(self, delta: float) -> bool:
        entity_id = self.config.get(CONF_HEAT_CURVE)
        if not entity_id:
            _LOGGER.warning("No heat curve entity configured")
            return False

        return await self._adjust_number_entity(entity_id, delta, "värmekurva")

    async def _adjust_heat_offset(self, delta: float) -> bool:
        entity_id = self.config.get(CONF_HEAT_OFFSET)
        if not entity_id:
            _LOGGER.warning("No heat offset entity configured")
            return False

        return await self._adjust_number_entity(entity_id, delta, "värmeoffset")

    async def _adjust_number_entity(
        self,
        entity_id: str,
        delta: float,
        name: str
    ) -> bool:
        state = self.hass.states.get(entity_id)
        if state is None:
            _LOGGER.error("Entity %s not found", entity_id)
            return False

        try:
            current_value = float(state.state)
        except (ValueError, TypeError):
            _LOGGER.error("Cannot parse current value of %s: %s", entity_id, state.state)
            return False

        new_value = current_value + delta

        attrs = state.attributes
        min_val = attrs.get("min", float("-inf"))
        max_val = attrs.get("max", float("inf"))
        new_value = max(min_val, min(max_val, new_value))

        _LOGGER.info(
            "Adjusting %s from %.1f to %.1f (delta: %.1f)",
            name, current_value, new_value, delta
        )

        domain = entity_id.split(".")[0]
        service = "set_value"

        try:
            await self.hass.services.async_call(
                domain,
                service,
                {ATTR_ENTITY_ID: entity_id, "value": new_value},
                blocking=True,
            )
            return True
        except Exception as e:
            _LOGGER.error("Failed to adjust %s: %s", name, e)
            return False

    def get_last_action_summary(self) -> str:
        if not self.last_action:
            return "Ingen åtgärd utförd ännu"

        action_texts = {
            "no_change": "Ingen ändring behövs",
            "skipped_manual_mode": "Hoppade över (manuellt läge)",
            "skipped_low_confidence": "Hoppade över (låg confidence)",
            "skipped_cooldown": "Hoppade över (cooldown)",
            "adjust_heat_curve": "Justerade värmekurva",
            "adjust_offset": "Justerade värmeoffset",
            "awaiting_confirmation": "Väntar på bekräftelse",
            "dismissed": "Avvisad av användare",
        }

        base_text = action_texts.get(self.last_action, self.last_action)

        if self.last_action_details.get("delta"):
            delta = self.last_action_details["delta"]
            sign = "+" if delta > 0 else ""
            base_text += f" ({sign}{delta})"

        return base_text
