import asyncio
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.start import async_at_started

from .const import DOMAIN, PLATFORMS, CONF_API_KEY
from .claude_service import ClaudeService
from .control_service import ControlService
from .coordinator import NibePilotCoordinator

_LOGGER = logging.getLogger(__name__)

STARTUP_DELAY_SECONDS = 60


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    api_key = entry.data[CONF_API_KEY]
    claude_service = ClaudeService(api_key)
    config = {**entry.data, **entry.options}
    control_service = ControlService(hass, config)

    coordinator = NibePilotCoordinator(
        hass,
        entry,
        claude_service,
        control_service,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_entry))

    async def _async_startup_complete(hass: HomeAssistant):
        _LOGGER.info(
            "Home Assistant started, waiting %d seconds before first analysis",
            STARTUP_DELAY_SECONDS
        )
        await asyncio.sleep(STARTUP_DELAY_SECONDS)
        coordinator.mark_startup_ready()
        await coordinator.async_request_refresh()

    async_at_started(hass, _async_startup_complete)

    _LOGGER.info("NibePilot setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("NibePilot unloaded")

    return unload_ok


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
