import pandas as pd
import pytest

from ahu_fdd.features import (
    cooling_per_valve,
    minutes_since_fan_on,
    outdoor_air_fraction,
    sat_error,
    sat_offset_at_rest,
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
