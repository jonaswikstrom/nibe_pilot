import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NibePilotCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NibePilotCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        NibePilotRefreshButton(coordinator, entry),
    ]

    async_add_entities(entities)


class NibePilotRefreshButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Kör analys"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: NibePilotCoordinator, entry: ConfigEntry):
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_refresh"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "NibePilot",
            "manufacturer": "Community",
            "model": "AI Heat Pump Controller",
            "sw_version": "1.1.1",
        }

    async def async_press(self) -> None:
        _LOGGER.info("Manual analysis triggered via button")
        await self.coordinator.async_request_refresh()
