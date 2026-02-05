import logging
from typing import Any
from homeassistant.core import HomeAssistant

from .const import NOTIFICATION_TAG

_LOGGER = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, hass: HomeAssistant, notify_service: str | None):
        self.hass = hass
        self._notify_service = notify_service
        self._pending_recommendation: dict[str, Any] | None = None

    def update_notify_service(self, notify_service: str | None):
        self._notify_service = notify_service

    @property
    def pending_recommendation(self) -> dict[str, Any] | None:
        return self._pending_recommendation

    def clear_pending(self):
        self._pending_recommendation = None

    async def send_recommendation_notification(
        self,
        recommendation: dict[str, Any],
    ) -> bool:
        if not self._notify_service:
            _LOGGER.warning("No notify service configured")
            return False

        self._pending_recommendation = recommendation

        action = recommendation.get("action", "no_change")
        if action == "no_change":
            return False

        reasoning = recommendation.get("reasoning", "Ingen förklaring")
        confidence = recommendation.get("confidence", 0)

        if action == "adjust_heat_curve":
            delta = recommendation.get("heat_curve_delta", 0)
            sign = "+" if delta > 0 else ""
            title = "NibePilot: Justera värmekurva"
            message = f"Förslag: Ändra värmekurva med {sign}{delta}\n\n{reasoning}\n\nConfidence: {confidence:.0%}"
        elif action == "adjust_offset":
            delta = recommendation.get("heat_offset_delta", 0)
            sign = "+" if delta > 0 else ""
            title = "NibePilot: Justera värmeoffset"
            message = f"Förslag: Ändra värmeoffset med {sign}{delta}\n\n{reasoning}\n\nConfidence: {confidence:.0%}"
        else:
            return False

        try:
            domain, service = self._notify_service.split(".", 1)
            await self.hass.services.async_call(
                domain,
                service,
                {
                    "title": title,
                    "message": message,
                    "data": {
                        "tag": NOTIFICATION_TAG,
                        "actions": [
                            {
                                "action": "APPLY",
                                "title": "Applicera",
                            },
                            {
                                "action": "IGNORE",
                                "title": "Ignorera",
                            },
                        ],
                    },
                },
                blocking=True,
            )
            _LOGGER.info("Sent recommendation notification via %s", self._notify_service)
            return True
        except Exception as e:
            _LOGGER.error("Failed to send notification: %s", e)
            return False
