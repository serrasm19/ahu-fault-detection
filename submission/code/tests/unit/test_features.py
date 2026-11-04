import pandas as pd
import pytest

from ahu_fdd.features import (
    add_deviations,
    add_features,
    ahu_baselines,
    cooling_per_valve,
    minutes_since_fan_on,
    outdoor_air_fraction,
    sat_error,
    sat_offset_at_rest,
    valve_curve,
)


def test_minutes_since_fan_on_restarts_with_each_start_and_each_ahu():
    df = pd.DataFrame(
        {
            "ahu_id": ["B3-AHU-01"] * 5 + ["B3-AHU-02"] * 2,
            "timestamp": pd.date_range("2025-03-10 09:00", periods=7, freq="5min"),
            "fan_status": [0, 1, 1, 0, 1, 1, 1],
        }
    )
    out = minutes_since_fan_on(df)
    assert out.isna().tolist() == [True, False, False, True, False, False, False]
    assert out.dropna().tolist() == [0, 5, 0, 0, 5]


def test_sat_error_is_supply_minus_setpoint():
    df = pd.DataFrame({"sat_c": [13.3, 12.0], "sat_sp_c": [13.0, 13.0]})
    assert sat_error(df).round(1).tolist() == [0.3, -1.0]


def test_outdoor_air_fraction_mixing_formula():
    # 20% outdoor air: MAT = 0.2 * 30 + 0.8 * 24 = 25.2. Second row: OAT too close to RAT
    df = pd.DataFrame({"mat_c": [25.2, 24.5], "rat_c": [24.0, 24.0], "oat_c": [30.0, 25.0]})
    out = outdoor_air_fraction(df, min_delta_c=2.0)
    assert out.iloc[0] == pytest.approx(0.2)
    assert pd.isna(out.iloc[1])


def test_cooling_per_valve_is_nan_when_valve_almost_closed():
    df = pd.DataFrame({"mat_c": [25.0, 25.0], "sat_c": [13.0, 20.0], "chw_valve_cmd_pct": [60, 10]})
    out = cooling_per_valve(df, min_valve_pct=20)
    assert out.iloc[0] == pytest.approx(20.0)  # 12 °C of cooling at 60% = 20 °C per 100%
    assert pd.isna(out.iloc[1])


def test_sat_offset_at_rest_only_after_the_fan_is_off_long_enough():
    df = pd.DataFrame(
        {
            "ahu_id": ["B3-AHU-08"] * 4,
            "timestamp": pd.date_range("2025-06-10 23:00", periods=4, freq="5min"),
            "fan_status": [1, 0, 0, 0],
            "sat_c": [13.0, 26.0, 27.0, 27.5],
            "mat_c": [25.0, 25.0, 25.0, 25.0],
        }
    )
    out = sat_offset_at_rest(df, min_minutes=5)
    # The fan stops on row 2 (0 minutes off), so rows 3 and 4 have been off for 5+ minutes
    assert out.isna().tolist() == [True, True, False, False]
    assert out.dropna().tolist() == [2.0, 2.5]


def _running_log(n=40, **cols):
    """A small log of one AHU with the fan on for n rows (5 minutes apart)."""
    base = {
        "ahu_id": "B3-AHU-01",
        "timestamp": pd.date_range("2025-03-10 09:00", periods=n, freq="5min"),
        "fan_status": 1,
        "fan_speed_pct": 60.0,
        "sat_c": 13.0,
        "sat_sp_c": 13.0,
        "mat_c": 25.0,
        "rat_c": 24.0,
        "oat_c": 30.0,
        "chw_valve_cmd_pct": 50.0,
        "oa_damper_cmd_pct": 20.0,
        "co2_ppm": float("nan"),
        "label": "normal",
    }
    base.update(cols)
    return pd.DataFrame(base)


def test_add_features_ignores_the_start_up():
    # Supply air 5 °C too warm for the first 30 minutes (start-up), then on target
    df = _running_log(sat_c=[18.0] * 6 + [13.0] * 34)
    out = add_features(df)
    # Start-up rows don't enter the smoothed error, so it is 0 once there are enough rows
    assert out["sat_error_1h"].dropna().eq(0).all()
    assert out["sat_error_1h"].iloc[:6].isna().all()


def test_add_features_valve_at_limit_share():
    df = _running_log(chw_valve_cmd_pct=[50.0] * 20 + [100.0] * 20)
    out = add_features(df)
    # The last 12 rows (1 hour) all have the command at 100%
    assert out["valve_at_limit_1h"].iloc[-1] == 1.0
    assert out["valve_at_limit_1h"].iloc[19] == 0.0


def test_add_features_carries_the_last_check_at_rest():
    # Fan off for 1.5 hours with the supply sensor 3 °C above the mixed air, then fan on
    df = _running_log(n=30, fan_status=[0] * 18 + [1] * 12, sat_c=[28.0] * 18 + [13.0] * 12)
    out = add_features(df)
    assert out["rest_offset"].iloc[12:18].eq(3.0).all()  # off for 60+ minutes
    assert out["last_rest_offset"].iloc[-1] == 3.0  # still known with the fan on


def test_baselines_and_deviations_compare_with_the_same_ahu():
    healthy = _running_log(n=60)
    faulty = _running_log(n=60, ahu_id="B3-AHU-02", sat_c=13.0)
    faulty.loc[48:, "sat_c"] = 20.0  # last hour: 7 °C too warm
    faulty.loc[48:, "label"] = "chw_valve_stuck"
    feats = add_features(pd.concat([healthy, faulty], ignore_index=True))
    base = ahu_baselines(feats)
    # The fault rows are not part of the normal
    assert base.loc["B3-AHU-02", "base_sat_error"] == 0.0
    out = add_deviations(feats, base, valve_curve(feats))
    assert out["sat_error_dev"].iloc[-1] == 7.0
    # Healthy rows need exactly their usual valve for their work
    assert out["valve_excess"].iloc[30] == pytest.approx(0.0)


def test_valve_excess_finds_more_valve_for_the_same_work():
    # Same cooling work all along (fan 60%, 12 °C cooled), but the valve opens from 50% to 80%
    df = _running_log(n=80, chw_valve_cmd_pct=[50.0] * 40 + [80.0] * 40)
    df.loc[40:, "label"] = "low_coil_capacity"
    feats = add_features(df)
    out = add_deviations(feats, ahu_baselines(feats), valve_curve(feats))
    assert out["valve_excess"].iloc[-1] == pytest.approx(30.0)
