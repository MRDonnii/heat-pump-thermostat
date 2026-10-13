"""Config flow for Heat Pump Thermostat."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
    CONF_COOL_TARGET,
    CONF_HEAT_PUMP,
    CONF_HEAT_TARGET,
    CONF_HYSTERESIS,
    CONF_START_HYSTERESIS,
    CONF_MANUAL_OVERRIDE_MINUTES,
    CONF_MIN_OFF_MINUTES,
    CONF_MIN_RUN_MINUTES,
    CONF_OPENING_SENSORS,
    CONF_OPENING_MIN_DELAY_MINUTES,
    CONF_OPENING_OFF_DELAY_MINUTES,
    CONF_OPENING_REDUCE_TO,
    CONF_OPENING_RESUME_DELAY_MINUTES,
    CONF_SENSOR_STABLE_SECONDS,
    CONF_SENSOR_LOSS_GRACE_SECONDS,
    CONF_SETPOINT_COMPENSATION,
    CONF_TEMPERATURE_SENSOR,
    CONF_THERMOSTATS_TO_DISABLE,
    DEFAULT_COOL_TARGET,
    DEFAULT_HEAT_TARGET,
    DEFAULT_HYSTERESIS,
    DEFAULT_START_HYSTERESIS,
    DEFAULT_MANUAL_OVERRIDE_MINUTES,
    DEFAULT_MIN_OFF_MINUTES,
    DEFAULT_MIN_RUN_MINUTES,
    DEFAULT_OPENING_MIN_DELAY_MINUTES,
    DEFAULT_OPENING_OFF_DELAY_MINUTES,
    DEFAULT_OPENING_REDUCE_TO,
    DEFAULT_OPENING_RESUME_DELAY_MINUTES,
    OPENING_REDUCE_MINIMUM,
    OPENING_REDUCE_SETPOINT,
    DEFAULT_SENSOR_STABLE_SECONDS,
    DEFAULT_SENSOR_LOSS_GRACE_SECONDS,
    DOMAIN,
)


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}

    def value(key: str, fallback: Any) -> Any:
        return defaults.get(key, fallback)

    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=value(CONF_NAME, "Varmepumpe termostat")): str,
            vol.Required(CONF_HEAT_PUMP, default=value(CONF_HEAT_PUMP, None)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate")
            ),
            vol.Required(
                CONF_TEMPERATURE_SENSOR,
                default=value(CONF_TEMPERATURE_SENSOR, None),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor", "number", "input_number"],
                    device_class="temperature",
                )
            ),
            vol.Optional(
                CONF_THERMOSTATS_TO_DISABLE,
                default=value(CONF_THERMOSTATS_TO_DISABLE, []),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate", multiple=True)
            ),
            vol.Optional(
                CONF_OPENING_SENSORS,
                default=value(CONF_OPENING_SENSORS, []),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
            ),
            vol.Required(
                CONF_OPENING_MIN_DELAY_MINUTES,
                default=value(
                    CONF_OPENING_MIN_DELAY_MINUTES, DEFAULT_OPENING_MIN_DELAY_MINUTES
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=180)),
            vol.Required(
                CONF_OPENING_OFF_DELAY_MINUTES,
                default=value(
                    CONF_OPENING_OFF_DELAY_MINUTES, DEFAULT_OPENING_OFF_DELAY_MINUTES
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=600)),
            vol.Required(
                CONF_OPENING_REDUCE_TO,
                default=value(CONF_OPENING_REDUCE_TO, DEFAULT_OPENING_REDUCE_TO),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[OPENING_REDUCE_SETPOINT, OPENING_REDUCE_MINIMUM],
                    translation_key="opening_reduce_to",
                )
            ),
            vol.Required(
                CONF_OPENING_RESUME_DELAY_MINUTES,
                default=value(
                    CONF_OPENING_RESUME_DELAY_MINUTES,
                    DEFAULT_OPENING_RESUME_DELAY_MINUTES,
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=180)),
            vol.Required(
                CONF_HEAT_TARGET, default=value(CONF_HEAT_TARGET, DEFAULT_HEAT_TARGET)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=16, max=30, step=1, unit_of_measurement="°C")
            ),
            vol.Required(
                CONF_COOL_TARGET, default=value(CONF_COOL_TARGET, DEFAULT_COOL_TARGET)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=18, max=32, step=1, unit_of_measurement="°C")
            ),
            vol.Required(
                CONF_START_HYSTERESIS,
                default=value(CONF_START_HYSTERESIS, DEFAULT_START_HYSTERESIS),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.0, max=2.0, step=0.1, unit_of_measurement="°C")
            ),
            vol.Required(
                CONF_HYSTERESIS, default=value(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.2, max=2.0, step=0.1, unit_of_measurement="°C")
            ),
            vol.Required(
                CONF_MIN_RUN_MINUTES,
                default=value(CONF_MIN_RUN_MINUTES, DEFAULT_MIN_RUN_MINUTES),
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=180)),
            vol.Required(
                CONF_MIN_OFF_MINUTES,
                default=value(CONF_MIN_OFF_MINUTES, DEFAULT_MIN_OFF_MINUTES),
            ): vol.All(vol.Coerce(int), vol.Range(min=3, max=60)),
            vol.Required(
                CONF_SENSOR_STABLE_SECONDS,
                default=value(CONF_SENSOR_STABLE_SECONDS, DEFAULT_SENSOR_STABLE_SECONDS),
            ): vol.All(vol.Coerce(int), vol.Range(min=30, max=900)),
            vol.Required(
                CONF_SENSOR_LOSS_GRACE_SECONDS,
                default=value(
                    CONF_SENSOR_LOSS_GRACE_SECONDS,
                    DEFAULT_SENSOR_LOSS_GRACE_SECONDS,
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
            vol.Required(
                CONF_MANUAL_OVERRIDE_MINUTES,
                default=value(CONF_MANUAL_OVERRIDE_MINUTES, DEFAULT_MANUAL_OVERRIDE_MINUTES),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=1440)),
            vol.Required(
                CONF_SETPOINT_COMPENSATION,
                default=value(CONF_SETPOINT_COMPENSATION, True),
            ): bool,
        }
    )


class HeatPumpThermostatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a heat-pump thermostat."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle initial setup."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=_schema())
        if int(user_input[CONF_OPENING_OFF_DELAY_MINUTES]) < int(user_input[CONF_OPENING_MIN_DELAY_MINUTES]):
            return self.async_show_form(
                step_id="user",
                data_schema=_schema(user_input),
                errors={CONF_OPENING_OFF_DELAY_MINUTES: "off_before_min"},
            )
        if float(user_input[CONF_COOL_TARGET]) <= float(user_input[CONF_HEAT_TARGET]):
            return self.async_show_form(
                step_id="user",
                data_schema=_schema(user_input),
                errors={CONF_COOL_TARGET: "cool_must_exceed_heat"},
            )
        await self.async_set_unique_id(user_input[CONF_HEAT_PUMP])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

    @staticmethod
    def async_get_options_flow(config_entry):
        return HeatPumpThermostatOptionsFlow(config_entry)


class HeatPumpThermostatOptionsFlow(config_entries.OptionsFlow):
    """Edit controller options."""

    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        current = {**self.entry.data, **self.entry.options}
        if user_input is None:
            return self.async_show_form(step_id="init", data_schema=_schema(current))
        if int(user_input[CONF_OPENING_OFF_DELAY_MINUTES]) < int(user_input[CONF_OPENING_MIN_DELAY_MINUTES]):
            return self.async_show_form(
                step_id="init",
                data_schema=_schema(user_input),
                errors={CONF_OPENING_OFF_DELAY_MINUTES: "off_before_min"},
            )
        if float(user_input[CONF_COOL_TARGET]) <= float(user_input[CONF_HEAT_TARGET]):
            return self.async_show_form(
                step_id="init",
                data_schema=_schema(user_input),
                errors={CONF_COOL_TARGET: "cool_must_exceed_heat"},
            )
        return self.async_create_entry(title="", data=user_input)
