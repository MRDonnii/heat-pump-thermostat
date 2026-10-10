"""Release button: drop every hold and return to automatic control now."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Add the release button."""
    async_add_entities([ReleaseButton(hass, entry)])


class ReleaseButton(ButtonEntity):
    """Clear manual override, door/window pause and start waits."""

    _attr_has_entity_name = True
    _attr_translation_key = "release"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_release"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}}

    async def async_press(self) -> None:
        thermostat = self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id)
        if thermostat is not None:
            await thermostat.async_release()
