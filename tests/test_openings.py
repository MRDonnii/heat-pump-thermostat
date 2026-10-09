"""Door/window staging: turn down after 5 min, switch off after 20 min, resume after 10 min closed."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.heat_pump_thermostat import climate as hpt_climate
from custom_components.heat_pump_thermostat.const import DOMAIN

PUMP = "climate.fake_pump"
SENSOR = "sensor.room_temperature"
DOOR = "binary_sensor.door"


class Clock:
    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, minutes: float) -> None:
        self.now += minutes * 60


class FakePump:
    """A heat pump that, like the Qlima units, silently ignores 16 °C in heat mode."""

    def __init__(self, hass, reject_heat_below: float = 17) -> None:
        self.hass = hass
        self.reject_heat_below = reject_heat_below
        self.state = "heat"
        self.target = 25.0
        self.calls: list[tuple[str, object]] = []
        self.publish()

    def register(self) -> None:
        # Registered after the climate component is loaded, so these fake
        # services replace the real ones for the stub pump entity.
        self.hass.services.async_register("climate", "set_temperature", self._set_temperature)
        self.hass.services.async_register("climate", "set_hvac_mode", self._set_hvac_mode)

    def publish(self) -> None:
        self.hass.states.async_set(
            PUMP,
            self.state,
            {"min_temp": 16, "max_temp": 32, "temperature": self.target, "current_temperature": 20},
        )

    async def _set_temperature(self, call) -> None:
        if call.data["entity_id"] in (PUMP, [PUMP]):
            value = float(call.data["temperature"])
            self.calls.append(("temperature", value))
            if self.state == "heat" and value < self.reject_heat_below:
                return  # accepted by the API, ignored by the unit
            self.target = value
            self.publish()

    async def _set_hvac_mode(self, call) -> None:
        if call.data["entity_id"] in (PUMP, [PUMP]):
            self.calls.append(("mode", call.data["hvac_mode"]))
            self.state = call.data["hvac_mode"]
            self.publish()


@pytest.fixture
def clock():
    c = Clock()
    with patch.object(hpt_climate, "time", c), patch.object(hpt_climate, "_TARGET_CONFIRM_SECONDS", 1):
        yield c


async def _setup(hass, clock, room_temp: float = 19.0):
    pump = FakePump(hass)
    hass.states.async_set(SENSOR, str(room_temp), {"unit_of_measurement": "°C"})
    hass.states.async_set(DOOR, "off")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test pump",
        data={
            "name": "Test pump",
            "heat_pump": PUMP,
            "temperature_sensor": SENSOR,
            "opening_sensors": [DOOR],
            "heat_target": 22,
            "cool_target": 25,
            "min_run_minutes": 20,
            "min_off_minutes": 10,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    pump.register()
    entity = hass.data[DOMAIN][entry.entry_id]
    await entity.async_set_hvac_mode("heat")
    clock.advance(3)  # past the startup grace / sensor stability
    await entity._evaluate("periodic")
    await hass.async_block_till_done()
    return pump, entity


async def _tick(hass, entity, clock, minutes: float) -> None:
    clock.advance(minutes)
    entity._periodic_update(None)
    await hass.async_block_till_done()


async def _set_door(hass, state: str) -> None:
    hass.states.async_set(DOOR, state)
    await hass.async_block_till_done()


async def test_turn_down_then_off_then_resume(hass, clock):
    pump, entity = await _setup(hass, clock)
    assert pump.state == "heat"
    assert entity.extra_state_attributes["active_mode"] == "heat"

    await _set_door(hass, "on")
    await _tick(hass, entity, clock, 4)
    assert entity.extra_state_attributes["opening_stage"] == "none"
    assert pump.state == "heat" and pump.target != 17

    # 5 min: turned down to the lowest target the unit really accepts (16 is ignored).
    await _tick(hass, entity, clock, 1.1)
    attrs = entity.extra_state_attributes
    assert attrs["opening_stage"] == "min"
    assert pump.state == "heat"
    assert pump.target == 17
    assert attrs["min_heat_target_accepted"] == 17
    assert ("temperature", 16.0) in pump.calls

    # 20 min: switched off completely.
    await _tick(hass, entity, clock, 15)
    assert entity.extra_state_attributes["opening_stage"] == "off"
    assert pump.state == "off"
    assert entity.hvac_mode == "heat"  # our own OFF is not mirrored as a remote stop

    # Closed 9 min, briefly reopened, closed again: still off, stage kept.
    await _set_door(hass, "off")
    await _tick(hass, entity, clock, 9)
    assert pump.state == "off"
    await _set_door(hass, "on")
    await _tick(hass, entity, clock, 0.2)
    await _set_door(hass, "off")
    await _tick(hass, entity, clock, 9)
    assert entity.extra_state_attributes["opening_stage"] == "off"
    assert pump.state == "off"

    # 10 min closed in a row: normal control resumes and the cold room is heated again.
    await _tick(hass, entity, clock, 1.5)
    assert entity.extra_state_attributes["opening_stage"] == "none"
    await _tick(hass, entity, clock, 0.5)
    assert pump.state == "heat"
    assert pump.target > 17


async def test_short_openings_accumulate(hass, clock):
    pump, entity = await _setup(hass, clock)
    for _ in range(3):
        await _set_door(hass, "on")
        await _tick(hass, entity, clock, 2)
        await _set_door(hass, "off")
        await _tick(hass, entity, clock, 1)
    assert entity.extra_state_attributes["opening_stage"] == "min"
    assert pump.target == 17


async def test_opening_never_switches_a_stopped_unit_on(hass, clock):
    pump, entity = await _setup(hass, clock, room_temp=24.0)  # warm: no heat demand
    # Unit stopped (e.g. user turned the physical unit off before the door opened).
    pump.state = "off"
    pump.publish()
    await hass.async_block_till_done()
    clock.advance(2)
    await _set_door(hass, "on")
    await _tick(hass, entity, clock, 6)
    assert pump.state == "off"
    await _tick(hass, entity, clock, 20)
    assert pump.state == "off"


async def test_learned_minimum_is_reused(hass, clock):
    pump, entity = await _setup(hass, clock)
    await _set_door(hass, "on")
    await _tick(hass, entity, clock, 6)
    assert pump.target == 17
    first_calls = len(pump.calls)
    await _set_door(hass, "off")
    await _tick(hass, entity, clock, 11)
    await _tick(hass, entity, clock, 1)
    await _set_door(hass, "on")
    await _tick(hass, entity, clock, 6)
    assert pump.target == 17
    later = pump.calls[first_calls:]
    assert ("temperature", 16.0) not in later
