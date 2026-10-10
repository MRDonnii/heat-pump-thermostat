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
        self.fan = "auto"
        self.swing = "off"
        self.swing_h = "off"
        self.preset = "comfort"
        self.calls: list[tuple[str, object]] = []
        self.publish()

    def register(self) -> None:
        # Registered after the climate component is loaded, so these fake
        # services replace the real ones for the stub pump entity.
        self.hass.services.async_register("climate", "set_temperature", self._set_temperature)
        self.hass.services.async_register("climate", "set_hvac_mode", self._set_hvac_mode)
        for service, attr, key in (
            ("set_fan_mode", "fan", "fan_mode"),
            ("set_swing_mode", "swing", "swing_mode"),
            ("set_swing_horizontal_mode", "swing_h", "swing_horizontal_mode"),
            ("set_preset_mode", "preset", "preset_mode"),
        ):
            self.hass.services.async_register("climate", service, self._setter(attr, key))

    def _setter(self, attr, key):
        async def handler(call) -> None:
            self.calls.append((key, call.data[key]))
            setattr(self, attr, call.data[key])
            self.publish(call.context)

        return handler

    def publish(self, context=None) -> None:
        self.hass.states.async_set(
            PUMP,
            self.state,
            {
                "min_temp": 16, "max_temp": 32, "temperature": self.target, "current_temperature": 20,
                "hvac_modes": ["off", "cool", "heat", "dry", "fan_only", "heat_cool"],
                "fan_modes": ["low", "medium", "high", "auto"], "fan_mode": self.fan,
                "swing_modes": ["off", "on"], "swing_mode": self.swing,
                "swing_horizontal_modes": ["on", "off"], "swing_horizontal_mode": self.swing_h,
                "preset_modes": ["eco", "comfort"], "preset_mode": self.preset,
            },
            context=context,
        )

    async def _set_temperature(self, call) -> None:
        if call.data["entity_id"] in (PUMP, [PUMP]):
            value = float(call.data["temperature"])
            self.calls.append(("temperature", value))
            if self.state == "heat" and value < self.reject_heat_below:
                return  # accepted by the API, ignored by the unit
            self.target = value
            self.publish(call.context)

    async def _set_hvac_mode(self, call) -> None:
        if call.data["entity_id"] in (PUMP, [PUMP]):
            self.calls.append(("mode", call.data["hvac_mode"]))
            self.state = call.data["hvac_mode"]
            self.publish(call.context)


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


async def test_user_restart_is_not_held_by_min_off(hass, clock):
    """Off and on again by the user starts at once (the unit protects its compressor)."""
    pump, entity = await _setup(hass, clock)
    assert pump.state == "heat"
    await entity.async_set_hvac_mode("off")
    await hass.async_block_till_done()
    assert pump.state == "off"
    clock.advance(0.2)
    await entity.async_set_hvac_mode("heat")
    await hass.async_block_till_done()
    assert pump.state == "heat"
    assert entity.extra_state_attributes["active_mode"] == "heat"


async def test_automatic_restart_still_waits_for_min_off(hass, clock):
    pump, entity = await _setup(hass, clock, room_temp=19.0)
    # Room gets warm -> automatic stop (neutral), then cold again shortly after.
    clock.advance(25)  # past minimum run time
    hass.states.async_set(SENSOR, "23.0", {"unit_of_measurement": "°C"})
    await hass.async_block_till_done()
    clock.advance(3)
    await entity._evaluate("periodic")
    await hass.async_block_till_done()
    assert entity.extra_state_attributes["active_mode"] == "off"
    hass.states.async_set(SENSOR, "20.0", {"unit_of_measurement": "°C"})
    await hass.async_block_till_done()
    clock.advance(3)
    await entity._evaluate("periodic")
    await hass.async_block_till_done()
    attrs = entity.extra_state_attributes
    assert attrs["active_mode"] == "off"
    assert attrs["pending_mode"] == "heat"
    assert 0 < attrs["start_wait_minutes"] <= 10


async def test_user_command_on_unit_is_manual_even_right_after_our_command(hass, clock):
    from homeassistant.core import Context

    pump, entity = await _setup(hass, clock)
    await entity.async_set_hvac_mode("off")
    await hass.async_block_till_done()
    assert pump.state == "off"
    # Within the echo guard window, the user switches the unit on from HA.
    clock.advance(0.3)
    await hass.services.async_call(
        "climate", "set_hvac_mode", {"entity_id": PUMP, "hvac_mode": "heat"},
        blocking=True, context=Context(user_id="user-1"),
    )
    await hass.async_block_till_done()
    attrs = entity.extra_state_attributes
    assert entity.hvac_mode == "heat"
    assert attrs["active_mode"] == "heat"
    assert entity.preset_mode == "manual"


async def test_fan_and_swing_pass_through(hass, clock):
    from homeassistant.components.climate import ClimateEntityFeature

    pump, entity = await _setup(hass, clock)
    assert entity.supported_features & ClimateEntityFeature.FAN_MODE
    assert entity.supported_features & ClimateEntityFeature.SWING_MODE
    assert entity.fan_modes == ["low", "medium", "high", "auto"]
    await entity.async_set_fan_mode("high")
    await entity.async_set_swing_mode("on")
    await entity.async_set_swing_horizontal_mode("on")
    await hass.async_block_till_done()
    assert (pump.fan, pump.swing, pump.swing_h) == ("high", "on", "on")
    assert entity.fan_mode == "high" and entity.swing_mode == "on"
    # Passing settings through is not a manual override.
    assert entity.preset_mode == "auto"


async def test_dry_mode_and_door_staging(hass, clock):
    pump, entity = await _setup(hass, clock)
    assert "dry" in entity.hvac_modes and "fan_only" in entity.hvac_modes
    await entity.async_set_hvac_mode("dry")
    await hass.async_block_till_done()
    assert pump.state == "dry"
    assert entity.hvac_action == "drying"
    await _set_door(hass, "on")
    await _tick(hass, entity, clock, 6)
    assert pump.state == "dry"  # no turn-down stage for dry/fan
    await _tick(hass, entity, clock, 15)
    assert pump.state == "off"
    await _set_door(hass, "off")
    await _tick(hass, entity, clock, 10.5)
    await _tick(hass, entity, clock, 0.5)
    assert pump.state == "dry"


async def test_unit_preset_select(hass, clock):
    pump, entity = await _setup(hass, clock)
    ids = [s.entity_id for s in hass.states.async_all("select")]
    assert ids, ids
    sel = ids[0]
    state = hass.states.get(sel)
    assert state.state == "comfort", (sel, state)
    await hass.services.async_call(
        "select", "select_option",
        {"entity_id": sel, "option": "eco"}, blocking=True,
    )
    await hass.async_block_till_done()
    assert pump.preset == "eco"
    assert hass.states.get(sel).state == "eco"


async def test_dry_chosen_on_unit_becomes_thermostat_mode(hass, clock):
    pump, entity = await _setup(hass, clock)
    clock.advance(3)  # past the echo guard of our own start command
    pump.state = "dry"
    pump.publish()
    await hass.async_block_till_done()
    assert entity.hvac_mode == "dry"
    assert entity.extra_state_attributes["active_mode"] == "dry"
