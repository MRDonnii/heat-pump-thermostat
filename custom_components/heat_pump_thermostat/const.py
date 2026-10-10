"""Constants for Heat Pump Thermostat."""

DOMAIN = "heat_pump_thermostat"

CONF_HEAT_PUMP = "heat_pump"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_THERMOSTATS_TO_DISABLE = "thermostats_to_disable"
CONF_OPENING_SENSORS = "opening_sensors"
CONF_OPENING_OFF_DELAY_SECONDS = "opening_off_delay_seconds"  # legacy (<= 0.1.x), no longer used
CONF_OPENING_MIN_DELAY_MINUTES = "opening_min_delay_minutes"
CONF_OPENING_OFF_DELAY_MINUTES = "opening_off_delay_minutes"
CONF_OPENING_RESUME_DELAY_MINUTES = "opening_resume_delay_minutes"
CONF_HEAT_TARGET = "heat_target"
CONF_COOL_TARGET = "cool_target"
CONF_HYSTERESIS = "hysteresis"
CONF_MIN_RUN_MINUTES = "min_run_minutes"
CONF_MIN_OFF_MINUTES = "min_off_minutes"
CONF_SENSOR_STABLE_SECONDS = "sensor_stable_seconds"
CONF_SENSOR_LOSS_GRACE_SECONDS = "sensor_loss_grace_seconds"
CONF_MANUAL_OVERRIDE_MINUTES = "manual_override_minutes"
CONF_SETPOINT_COMPENSATION = "setpoint_compensation"

DEFAULT_HEAT_TARGET = 21.0
DEFAULT_COOL_TARGET = 24.0
DEFAULT_HYSTERESIS = 0.5
DEFAULT_MIN_RUN_MINUTES = 20
DEFAULT_MIN_OFF_MINUTES = 10
DEFAULT_SENSOR_STABLE_SECONDS = 120
DEFAULT_SENSOR_LOSS_GRACE_SECONDS = 300
DEFAULT_MANUAL_OVERRIDE_MINUTES = 120
DEFAULT_OPENING_OFF_DELAY_SECONDS = 120  # legacy
DEFAULT_OPENING_MIN_DELAY_MINUTES = 5
DEFAULT_OPENING_OFF_DELAY_MINUTES = 20
DEFAULT_OPENING_RESUME_DELAY_MINUTES = 10

PRESET_AUTO = "auto"
PRESET_MANUAL = "manual"

OPENING_STAGE_NONE = "none"
OPENING_STAGE_MIN = "min"
OPENING_STAGE_OFF = "off"

PLATFORMS = ["climate", "select", "sensor", "button"]

# Dispatcher signal sent whenever a thermostat writes its state.
SIGNAL_UPDATE = "heat_pump_thermostat_update_{}"

# Countdowns exposed as timestamp sensors, in display order.
COUNTDOWN_MANUAL_OVERRIDE = "manual_override"
COUNTDOWN_OPENING_REDUCE = "opening_reduce"
COUNTDOWN_OPENING_OFF = "opening_off"
COUNTDOWN_OPENING_RESUME = "opening_resume"
COUNTDOWN_START_ALLOWED = "start_allowed"
COUNTDOWN_MIN_RUN = "min_run"
COUNTDOWN_SENSOR_LOSS = "sensor_loss"
COUNTDOWNS = (
    COUNTDOWN_MANUAL_OVERRIDE,
    COUNTDOWN_OPENING_REDUCE,
    COUNTDOWN_OPENING_OFF,
    COUNTDOWN_OPENING_RESUME,
    COUNTDOWN_START_ALLOWED,
    COUNTDOWN_MIN_RUN,
    COUNTDOWN_SENSOR_LOSS,
)

# What the thermostat is doing right now (enum sensor).
STATUSES = (
    "off",
    "manual",
    "opening_off",
    "opening_reduced",
    "opening_resume_wait",
    "opening_reduce_wait",
    "sensor_lost",
    "start_wait",
    "heating",
    "cooling",
    "drying",
    "fan_only",
    "idle",
)
