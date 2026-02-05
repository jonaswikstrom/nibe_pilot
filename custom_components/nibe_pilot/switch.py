import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NibePilotCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NibePilotCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([NibePilotAutoModeSwitch(coordinator, entry)])


class NibePilotAutoModeSwitch(CoordinatorEntity[NibePilotCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Auto-mode"
    _attr_icon = "mdi:robot"

    def __init__(self, coordinator: NibePilotCoordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_auto_mode"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "NibePilot",
            "manufacturer": "Community",
            "model": "AI Heat Pump Controller",
            "sw_version": "1.2.1",
        }

    @property
    def is_on(self) -> bool:
        return self.coordinator.auto_mode

    async def async_turn_on(self, **kwargs):
        self.coordinator.set_auto_mode(True)
        self.async_write_ha_state()
        _LOGGER.info("NibePilot auto-mode enabled")

    async def async_turn_off(self, **kwargs):
        self.coordinator.set_auto_mode(False)
        self.async_write_ha_state()
        _LOGGER.info("NibePilot auto-mode disabled")

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}

        return {
            "last_recommendation": self.coordinator.data.get("recommendation", {}).get("action"),
            "last_action": self.coordinator.data.get("last_action"),
        }
