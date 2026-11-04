import pandas as pd

from ahu_fdd.rules import rule_predictions

COLS = {
    "minutes_on": 60.0,
    "sat_error_dev": 0.0,
    "valve_at_limit_1h": 0.0,
    "oa_fraction_dev": 0.0,
    "oa_fraction_1h": 0.15,
    "rest_offset_dev": 0.0,
    "valve_excess": 0.0,
    "valve_dev": 0.0,
}


def _row(**changes):
    return {**COLS, **changes}


def test_each_rule_finds_its_fault():
    df = pd.DataFrame(
        [
            _row(),
            _row(sat_error_dev=8.0, valve_at_limit_1h=1.0),
            _row(oa_fraction_dev=-0.15, oa_fraction_1h=0.0),
            _row(rest_offset_dev=-2.5),
            _row(valve_excess=20.0),
        ]
    )
    assert rule_predictions(df).tolist() == [
        "normal",
        "chw_valve_stuck",
        "oa_damper_stuck",
        "sat_sensor_bias",
        "low_coil_capacity",
    ]


def test_no_alarm_during_start_up_and_tap_wins_over_weak_radiator():
    df = pd.DataFrame(
        [
            _row(minutes_on=10.0, sat_error_dev=8.0, valve_at_limit_1h=1.0),
            _row(sat_error_dev=8.0, valve_at_limit_1h=1.0, valve_excess=40.0),
        ]
    )
    assert rule_predictions(df).tolist() == ["normal", "chw_valve_stuck"]
