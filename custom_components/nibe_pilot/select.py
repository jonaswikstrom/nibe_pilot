import logging
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONTROL_MODE_MANUAL,
    CONTROL_MODE_NOTIFY,
    CONTROL_MODE_AUTO,
)
from .coordinator import NibePilotCoordinator

_LOGGER = logging.getLogger(__name__)

CONTROL_MODE_OPTIONS = {
    CONTROL_MODE_MANUAL: "Manuellt",
    CONTROL_MODE_NOTIFY: "Notis",
    CONTROL_MODE_AUTO: "Automatiskt",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NibePilotCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NibePilotControlModeSelect(coordinator, entry)])


class NibePilotControlModeSelect(CoordinatorEntity[NibePilotCoordinator], SelectEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "control_mode"
    _attr_icon = "mdi:robot"

    def __init__(self, coordinator: NibePilotCoordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_control_mode"
        self._attr_options = list(CONTROL_MODE_OPTIONS.values())

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "NibePilot",
            "manufacturer": "Community",
            "model": "AI Heat Pump Controller",
            "sw_version": "1.3.2",
        }

    @property
    def current_option(self) -> str:
        return CONTROL_MODE_OPTIONS.get(
            self.coordinator.control_mode,
            CONTROL_MODE_OPTIONS[CONTROL_MODE_MANUAL]
        )

    async def async_select_option(self, option: str) -> None:
        mode_map = {v: k for k, v in CONTROL_MODE_OPTIONS.items()}
        mode = mode_map.get(option, CONTROL_MODE_MANUAL)
        self.coordinator.set_control_mode(mode)
        self.async_write_ha_state()
        _LOGGER.info("NibePilot control mode set to %s", mode)

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}

        return {
            "last_recommendation": self.coordinator.data.get("recommendation", {}).get("action"),
            "last_action": self.coordinator.data.get("last_action"),
        }
