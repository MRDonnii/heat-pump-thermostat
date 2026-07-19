# Heat Pump Thermostat

![Heat Pump Thermostat](custom_components/heat_pump_thermostat/brand/logo.png)

A Home Assistant custom integration that creates a virtual climate entity for an existing heat pump. It controls heating and cooling from an external room-temperature sensor while limiting command chatter, protecting compressor run times, handling open windows, and respecting manual control.

## Features

- Uses any Home Assistant `climate` entity as the physical heat pump.
- Uses an external temperature sensor instead of the heat pump's internal sensor.
- Provides heating, cooling, and automatic heat/cool targets.
- Applies configurable hysteresis, minimum run time, and minimum off time.
- Keeps the heat pump powered in a neutral mode when there is no demand instead of repeatedly switching it off and on.
- Optional setpoint compensation for heat pumps that only expose their own internal temperature.
- Pauses operation after configured doors or windows have remained open for a chosen delay.
- Resumes only after the configured closing delay.
- Handles temporary temperature-sensor loss with a configurable grace period.
- Detects manual remote-control changes without continuously overwriting them.
- Treats a physical `off` command as a persistent stop: the virtual thermostat stays off until the user explicitly turns it on again.
- Can optionally pause selected climate entities while the heat pump is actively heating or cooling. The list may be left empty.
- Restores setpoints and controller state after a Home Assistant restart.
- Exposes diagnostic attributes such as active mode, neutral mode, pending mode, opening pause, command counters, and paused thermostats.
- Supports multiple independent heat pumps by adding the integration once per unit.

## Installation with HACS

1. Open HACS in Home Assistant.
2. Open **Integrations**, select the menu, and choose **Custom repositories**.
3. Add `https://github.com/MRDonnii/heat-pump-thermostat` as an **Integration** repository.
4. Install **Heat Pump Thermostat**.
5. Restart Home Assistant.
6. Go to **Settings → Devices & services → Add integration** and search for **Heat Pump Thermostat**.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MRDonnii&repository=heat-pump-thermostat&category=integration)

## Manual installation

Copy `custom_components/heat_pump_thermostat` into the `custom_components` directory in your Home Assistant configuration, restart Home Assistant, and add the integration from **Settings → Devices & services**.

## Configuration

Each integration entry controls one physical heat pump.

| Option | Description |
| --- | --- |
| Name | Name of the virtual thermostat. |
| Heat pump | Physical `climate` entity to control. |
| Temperature sensor | External room-temperature entity. |
| Thermostats to disable | Optional climate entities to pause during active heating or cooling. Leave empty to disable this behavior. |
| Opening sensors | Door and window sensors that can pause the heat pump. |
| Opening delay | How long an opening must remain open before pausing. |
| Resume delay | How long all openings must remain closed before resuming. |
| Heat and cool targets | Desired room-temperature setpoints. |
| Hysteresis | Temperature margin used to prevent rapid changes. |
| Minimum run/off times | Compressor-friendly transition limits. |
| Sensor stability/grace | Delays for recovering from changes or missing sensor data. |
| Remote override | How long manual heat, cool, or temperature changes are respected. A physical off is persistent and does not expire. |
| Setpoint compensation | Adjusts the physical target so the external sensor governs room temperature. |

All options can be changed later with **Configure** on the integration entry.

## Operating behavior

Set the desired temperature and HVAC mode on the virtual `climate.varmepumpe_*` entity. Dashboards and automations should control the virtual entity, while vendor-specific fan, swing, sleep, or preset controls may still target the physical heat pump.

When there is no heating or cooling demand, the integration keeps the physical unit in a neutral mode at a non-demanding target. Explicitly turning the virtual thermostat off turns the physical unit off. Turning the physical unit off with its remote also turns the virtual thermostat off persistently.

Window and door pauses only affect the heat pump. Selected secondary thermostats are only paused if they were explicitly configured; an empty list means no radiator or zone thermostats are touched.

## Support

Report problems and feature requests in [GitHub Issues](https://github.com/MRDonnii/heat-pump-thermostat/issues). Include your Home Assistant version, the physical climate integration, relevant entity states, and sanitized logs. Never include access tokens, passwords, public IP addresses, or other credentials.

## License

MIT
