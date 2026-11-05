import pandas as pd

from ahu_fdd.postprocess import (
    bridge_short_gaps,
    drop_short_alarms,
    one_type_per_alarm,
    type_from_rules,
)


def test_drop_short_alarms_keeps_long_ones_across_fan_off_rows():
    # 2 alarm rows (short), then 3 alarm rows with a fan-off row in the middle (long enough)
    df = pd.DataFrame(
        {
            "ahu_id": "B1-AHU-04",
            "timestamp": pd.date_range("2025-03-24 08:00", periods=8, freq="5min"),
            "fan_status": [1, 1, 1, 1, 1, 0, 1, 1],
        }
    )
    pred = pd.Series(["oa_damper_stuck"] * 2 + ["normal"] + ["chw_valve_stuck"] * 5)
    out = drop_short_alarms(df, pred, min_rows=3)
    assert out.tolist() == ["normal"] * 3 + ["chw_valve_stuck"] * 5


def test_one_type_per_alarm_uses_the_main_type():
    df = pd.DataFrame(
        {
            "ahu_id": "B3-AHU-02",
            "timestamp": pd.date_range("2025-03-29 10:00", periods=6, freq="5min"),
            "fan_status": 1,
        }
    )
    pred = pd.Series(
        [
            "normal",
            "low_coil_capacity",
            "chw_valve_stuck",
            "low_coil_capacity",
            "low_coil_capacity",
            "normal",
        ]
    )
    out = one_type_per_alarm(df, pred)
    assert out.tolist() == ["normal"] + ["low_coil_capacity"] * 4 + ["normal"]


def _on(n, ahu="B3-AHU-06"):
    return pd.DataFrame(
        {
            "ahu_id": ahu,
            "timestamp": pd.date_range("2025-07-25 09:00", periods=n, freq="5min"),
            "fan_status": 1,
        }
    )


def test_bridge_short_gaps_joins_two_alarms_but_not_the_ends():
    pred = pd.Series(
        ["normal"] + ["sat_sensor_bias"] * 2 + ["normal"] * 2 + ["sat_sensor_bias"] * 2 + ["normal"]
    )
    out = bridge_short_gaps(_on(8), pred, max_rows=2)
    # The 2-row gap is filled; the normal rows at the start and at the end stay normal
    assert out.tolist() == ["normal"] + ["sat_sensor_bias"] * 6 + ["normal"]


def test_type_from_rules_overrides_the_model_type_inside_an_alarm():
    model = pd.Series(["normal"] + ["chw_valve_stuck"] * 3 + ["normal"])
    rules = pd.Series(
        ["oa_damper_stuck", "normal", "low_coil_capacity", "low_coil_capacity", "normal"]
    )
    out = type_from_rules(_on(5), model, rules)
    # The rule outside the alarm (row 0) is ignored
    assert out.tolist() == ["normal"] + ["low_coil_capacity"] * 3 + ["normal"]
