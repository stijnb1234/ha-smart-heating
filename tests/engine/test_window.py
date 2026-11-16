from datetime import time, timedelta

from custom_components.smart_heating.engine import (
    Commands,
    EngineConfig,
    EngineInput,
    RoomConfig,
    ScheduleWindow,
    SensorReading,
    decide,
)

ALWAYS = (ScheduleWindow(frozenset(range(7)), time(0), time(23, 59)),)


class Home:
    """Feeds readings and the engine's own state back in, one minute at a time."""

    def __init__(self, clock, **room_kwargs):
        self.clock = clock
        room = RoomConfig(name="bedroom", schedule=ALWAYS, **room_kwargs)
        self.config = EngineConfig(rooms=(room,), boiler_low=10.0, boiler_high=22.0)
        self.history: list[SensorReading] = []
        self.commands = Commands()
        self.decision = None

    def step(self, temp, minutes=1):
        self.clock.advance(minutes=minutes)
        self.history.append(SensorReading(temp, self.clock.now()))
        self.decision = decide(
            EngineInput(
                config=self.config,
                now=self.clock.now(),
                anyone_home=True,
                learned={},
                last_commands=self.commands,
                trv_temps={"bedroom": self.history[-1]},
                temp_history={"bedroom": tuple(self.history)},
            )
        )
        self.commands = Commands(
            trv_setpoints=self.decision.trv_setpoints,
            window_paused_until=self.decision.window_paused_until,
        )
        return self.decision.trv_setpoints["bedroom"]


def settle(home, temp=19.0, minutes=15):
    for _ in range(minutes):
        home.step(temp)


def test_fast_drop_pauses_room_at_frost_hold(clock):
    home = Home(clock)
    settle(home)
    home.step(18.0)
    assert home.step(17.0) == 12.0


def test_slow_cooling_does_not_pause(clock):
    home = Home(clock)
    settle(home)
    temp = 19.0
    for _ in range(60):
        temp -= 0.03  # about 1.8 degC per hour
        assert home.step(temp) == 19.5


def test_small_dip_does_not_pause(clock):
    home = Home(clock)
    settle(home)
    assert home.step(18.6) == 19.5


def test_room_stays_paused_then_resumes(clock):
    home = Home(clock, window_pause=timedelta(minutes=20))
    settle(home)
    home.step(18.0)
    home.step(17.0)
    for _ in range(17):  # the 18.0 step already triggers (1.0 degC drop)
        assert home.step(17.0) == 12.0
    assert home.step(17.2) == 12.0  # 19 min after trigger: still paused
    assert home.step(17.4) == 19.5  # resumes after 20 min


def test_no_repeat_trigger_on_stale_drop_after_resume(clock):
    home = Home(clock, window_pause=timedelta(minutes=15))
    settle(home)
    home.step(17.0)
    for _ in range(14):
        home.step(17.0)
    assert home.step(17.0) == 19.5
    assert home.step(17.1) == 19.5


def test_disabled_room_never_pauses(clock):
    home = Home(clock, window_detection=False)
    settle(home)
    assert home.step(15.0) == 19.5


def test_sensitivity_tunable_per_room(clock):
    sensitive = Home(clock, window_drop=0.4)
    settle(sensitive)
    assert sensitive.step(18.5) == 12.0

    relaxed = Home(clock, window_drop=3.0)
    settle(relaxed)
    assert relaxed.step(17.0) == 19.5


def test_pause_duration_is_clamped_to_15_30_minutes(clock):
    home = Home(clock, window_pause=timedelta(minutes=60))
    settle(home)
    home.step(17.0)
    for _ in range(29):
        home.step(17.0)
    assert home.step(17.0) == 19.5


def test_default_sensitivity_catches_a_realistic_open_window(clock):
    home = Home(clock)
    settle(home)
    temp = 19.0
    for _ in range(15):
        temp -= 0.06  # 0.9 degC in 15 min, well below the old 1.5 degC / 10 min threshold
        home.step(temp)
    assert home.decision.trv_setpoints["bedroom"] == 12.0


def test_settling_back_from_an_overshoot_is_not_a_window(clock):
    home = Home(clock)  # target 19.5
    settle(home, temp=21.0)
    temp = 21.0
    for _ in range(20):
        temp -= 0.09  # 1.35 degC in 15 min, but only down to the target
        assert home.step(temp) == 19.5


def test_fall_below_target_after_an_overshoot_still_pauses(clock):
    home = Home(clock)
    settle(home, temp=21.0)
    home.step(19.5)
    assert home.step(18.5) == 12.0  # 1.0 below the target


def _with_room_sensor(home, trv_temp, room_temp, valve_known=False):
    """One step where the TRV sensor and a separate room sensor report different things."""
    home.clock.advance(minutes=1)
    now = home.clock.now()
    home.history.append(SensorReading(trv_temp, now))
    home.room_history.append(SensorReading(room_temp, now))
    home.decision = decide(
        EngineInput(
            config=home.config,
            now=now,
            anyone_home=True,
            learned={},
            last_commands=home.commands,
            trv_temps={"bedroom": home.history[-1]},
            external_temps={"bedroom": home.room_history[-1]},
            temp_history={"bedroom": tuple(home.history)},
            external_history={"bedroom": tuple(home.room_history)},
            valve_known=frozenset({"bedroom"}) if valve_known else frozenset(),
        )
    )
    home.commands = Commands(
        trv_setpoints=home.decision.trv_setpoints, window_paused_until=home.decision.window_paused_until
    )
    return home.decision.trv_setpoints["bedroom"]


def test_trv_sensor_swing_with_a_steady_room_is_not_a_window(clock):
    home = Home(clock)
    home.room_history = []
    for _ in range(15):
        _with_room_sensor(home, 19.0, 19.0)
    for _ in range(3):
        target = _with_room_sensor(home, 17.5, 19.0)  # radiator cooled, room unchanged
    assert target == 19.5


def test_trv_fall_that_shows_in_the_room_is_a_window(clock):
    home = Home(clock)
    home.room_history = []
    for _ in range(15):
        _with_room_sensor(home, 19.0, 19.0)
    _with_room_sensor(home, 17.5, 18.4)
    assert _with_room_sensor(home, 17.5, 18.3) == 12.0


def test_trv_with_valve_info_is_judged_by_its_own_sensor(clock):
    home = Home(clock)
    home.room_history = []
    for _ in range(15):
        _with_room_sensor(home, 19.0, 19.0, valve_known=True)
    # Valve was closed (not cooling), TRV falls, the stepped room sensor has not moved yet.
    assert _with_room_sensor(home, 17.5, 19.0, valve_known=True) == 12.0
