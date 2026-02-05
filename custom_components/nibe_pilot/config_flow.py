import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_UPDATE_INTERVAL,
    CONF_OUTDOOR_TEMP,
    CONF_INDOOR_TEMP,
    CONF_SUPPLY_TEMP,
    CONF_COMPRESSOR_FREQ,
    CONF_POWER_CONSUMPTION,
    CONF_HOT_WATER_TEMP,
    CONF_RETURN_TEMP,
    CONF_HEAT_CURVE,
    CONF_HEAT_OFFSET,
    CONF_SETPOINT,
    CONF_MANUAL_SETPOINT,
    CONF_WEATHER,
    CONF_ELECTRICITY_PRICE,
    CONF_MAX_HEAT_CURVE_DELTA,
    CONF_MAX_HEAT_OFFSET_DELTA,
    CONF_CONFIDENCE_THRESHOLD,
    CONF_COOLDOWN_MINUTES,
    CONF_BUILDING_TYPE,
    CONF_NOTIFY_SERVICE,
    CONF_CONTROL_MODE,
    CONTROL_MODE_MANUAL,
    CONTROL_MODE_NOTIFY,
    CONTROL_MODE_AUTO,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_MAX_HEAT_CURVE_DELTA,
    DEFAULT_MAX_HEAT_OFFSET_DELTA,
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_COOLDOWN_MINUTES,
)

_LOGGER = logging.getLogger(__name__)


class NibePilotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._data = {}

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            from .claude_service import ClaudeService

            service = ClaudeService(user_input[CONF_API_KEY])
            if await service.validate_api_key():
                self._data.update(user_input)
                return await self.async_step_sensors()
            else:
                errors["base"] = "invalid_api_key"

        schema = vol.Schema({
            vol.Required(CONF_API_KEY): str,
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=DEFAULT_UPDATE_INTERVAL
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5,
                    max=60,
                    step=5,
                    unit_of_measurement="min",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_sensors(self, user_input=None):
        errors = {}

        if user_input is not None:
            if not user_input.get(CONF_OUTDOOR_TEMP):
                errors[CONF_OUTDOOR_TEMP] = "required"
            elif not user_input.get(CONF_INDOOR_TEMP):
                errors[CONF_INDOOR_TEMP] = "required"
            elif not user_input.get(CONF_SUPPLY_TEMP):
                errors[CONF_SUPPLY_TEMP] = "required"

            if not errors:
                self._data.update(user_input)
                return await self.async_step_controls()

        schema = vol.Schema({
            vol.Required(CONF_OUTDOOR_TEMP): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(CONF_INDOOR_TEMP): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(CONF_SUPPLY_TEMP): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_RETURN_TEMP): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_COMPRESSOR_FREQ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_POWER_CONSUMPTION): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_HOT_WATER_TEMP): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
        })

        return self.async_show_form(
            step_id="sensors",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_controls(self, user_input=None):
        errors = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_external()

        schema = vol.Schema({
            vol.Optional(CONF_HEAT_CURVE): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["number", "input_number"])
            ),
            vol.Optional(CONF_HEAT_OFFSET): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["number", "input_number"])
            ),
            vol.Optional(CONF_SETPOINT): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["climate", "number", "input_number"])
            ),
            vol.Optional(CONF_MANUAL_SETPOINT): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=15,
                    max=25,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        })

        return self.async_show_form(
            step_id="controls",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_external(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)

            await self.async_set_unique_id(f"nibe_pilot_{self._data[CONF_API_KEY][:8]}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="NibePilot",
                data=self._data,
            )

        schema = vol.Schema({
            vol.Optional(CONF_WEATHER): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="weather")
            ),
            vol.Optional(CONF_ELECTRICITY_PRICE): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
        })

        return self.async_show_form(
            step_id="external",
            data_schema=schema,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return NibePilotOptionsFlow()


class NibePilotOptionsFlow(config_entries.OptionsFlow):
    def __init__(self):
        self._options_data = {}

    def _get_notify_services(self) -> list[dict[str, str]]:
        services = self.hass.services.async_services()
        notify_services = services.get("notify", {})
        options = [{"value": "", "label": "Ingen (inaktiverad)"}]
        for service_name in sorted(notify_services.keys()):
            full_name = f"notify.{service_name}"
            options.append({"value": full_name, "label": full_name})
        return options

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self._options_data = user_input
            return await self.async_step_safety()

        current = {**self.config_entry.data, **self.config_entry.options}
        notify_options = self._get_notify_services()

        schema = vol.Schema({
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=current.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5,
                    max=60,
                    step=5,
                    unit_of_measurement="min",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Optional(
                CONF_OUTDOOR_TEMP,
                description={"suggested_value": current.get(CONF_OUTDOOR_TEMP)}
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_INDOOR_TEMP,
                description={"suggested_value": current.get(CONF_INDOOR_TEMP)}
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_SUPPLY_TEMP,
                description={"suggested_value": current.get(CONF_SUPPLY_TEMP)}
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_WEATHER,
                description={"suggested_value": current.get(CONF_WEATHER)}
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="weather")
            ),
            vol.Optional(
                CONF_ELECTRICITY_PRICE,
                description={"suggested_value": current.get(CONF_ELECTRICITY_PRICE)}
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_BUILDING_TYPE,
                description={"suggested_value": current.get(CONF_BUILDING_TYPE)}
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "light", "label": "Lätt byggnad (snabb uppvärmning)"},
                        {"value": "medium", "label": "Normal byggnad"},
                        {"value": "heavy", "label": "Tung byggnad (stor termisk massa)"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_CONTROL_MODE,
                description={"suggested_value": current.get(CONF_CONTROL_MODE, CONTROL_MODE_MANUAL)}
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": CONTROL_MODE_MANUAL, "label": "Manuellt (visa endast rekommendationer)"},
                        {"value": CONTROL_MODE_NOTIFY, "label": "Notis (fråga innan ändring)"},
                        {"value": CONTROL_MODE_AUTO, "label": "Automatiskt (applicera direkt)"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_NOTIFY_SERVICE,
                description={"suggested_value": current.get(CONF_NOTIFY_SERVICE, "")}
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=notify_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )

    async def async_step_safety(self, user_input=None):
        if user_input is not None:
            self._options_data.update(user_input)
            return self.async_create_entry(title="", data=self._options_data)

        current = {**self.config_entry.data, **self.config_entry.options}

        schema = vol.Schema({
            vol.Required(
                CONF_MAX_HEAT_CURVE_DELTA,
                default=current.get(CONF_MAX_HEAT_CURVE_DELTA, DEFAULT_MAX_HEAT_CURVE_DELTA)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=10,
                    step=1,
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Required(
                CONF_MAX_HEAT_OFFSET_DELTA,
                default=current.get(CONF_MAX_HEAT_OFFSET_DELTA, DEFAULT_MAX_HEAT_OFFSET_DELTA)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=5,
                    step=1,
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Required(
                CONF_CONFIDENCE_THRESHOLD,
                default=current.get(CONF_CONFIDENCE_THRESHOLD, DEFAULT_CONFIDENCE_THRESHOLD)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.3,
                    max=0.95,
                    step=0.05,
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Required(
                CONF_COOLDOWN_MINUTES,
                default=current.get(CONF_COOLDOWN_MINUTES, DEFAULT_COOLDOWN_MINUTES)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=120,
                    step=5,
                    unit_of_measurement="min",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
        })

        return self.async_show_form(
            step_id="safety",
            data_schema=schema,
        )
