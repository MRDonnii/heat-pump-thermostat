"""Status and countdown sensors for each heat pump thermostat."""

from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import COUNTDOWNS, DOMAIN, SIGNAL_UPDATE, STATUSES


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Add the status, next-change and one countdown sensor per timer."""
    entities: list[SensorEntity] = [StatusSensor(hass, entry), NextChangeSensor(hass, entry)]
    entities += [CountdownSensor(hass, entry, key) for key in COUNTDOWNS]
    async_add_entities(entities)


def _as_datetime(value: float | None) -> datetime | None:
    return datetime.fromtimestamp(value, timezone.utc) if value is not None else None


class _ThermostatSensor(SensorEntity):
    """Follows the thermostat entity of the same config entry."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, key: str) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}}

    @property
    def _thermostat(self):
        return self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id)

    @property
    def available(self) -> bool:
        return self._thermostat is not None

    async def async_added_to_hass(self) -> None:
        @callback
        def _updated() -> None:
            self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE.format(self.entry.entry_id), _updated)
        )


class StatusSensor(_ThermostatSensor):
    """What the thermostat is doing: heating, door pause, manual override, ..."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(STATUSES)

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, entry, "status")

    @property
    def native_value(self) -> str | None:
        thermostat = self._thermostat
        return thermostat.status() if thermostat is not None else None


class NextChangeSensor(_ThermostatSensor):
    """When the first running timer ends, and which one it is."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, entry, "next_change")

    @property
    def native_value(self) -> datetime | None:
        thermostat = self._thermostat
        return _as_datetime(thermostat.next_change()[1]) if thermostat is not None else None

    @property
    def extra_state_attributes(self):
        thermostat = self._thermostat
        return {"event": thermostat.next_change()[0] if thermostat is not None else None}


class CountdownSensor(_ThermostatSensor):
    """End time of one timer; unknown while that timer is not running."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, key: str) -> None:
        super().__init__(hass, entry, f"countdown_{key}")
        self._key = key

    @property
    def native_value(self) -> datetime | None:
        thermostat = self._thermostat
        return _as_datetime(thermostat.countdowns()[self._key]) if thermostat is not None else None
