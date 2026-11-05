import pandas as pd
import pytest

from ahu_fdd.simulate import inject_fault


def _log(n=6, fan=1):
    """A healthy AHU: cooling 12 °C with the valve at 50%, 20% outdoor air."""
    return pd.DataFrame(
        {
            "ahu_id": "B1-AHU-01",
            "timestamp": pd.date_range("2025-03-10 10:00", periods=n, freq="h"),
            "fan_status": fan,
            "sat_c": 13.0,
            "sat_sp_c": 13.0,
            "mat_c": 25.0,
            "rat_c": 24.0,
            "oat_c": 29.0,
            "chwst_c": 7.0,
            "chw_valve_cmd_pct": 50.0,
            "oa_damper_cmd_pct": 20.0,
            "co2_ppm": 800.0,
        }
    )


def _inject(df, fault, size, start="2025-03-10 12:00", end="2025-03-10 14:00"):
    return inject_fault(df, ahu_id="B1-AHU-01", fault=fault, start=start, end=end, size=size)


def test_only_the_window_changes():
    out = _inject(_log(), "chw_valve_stuck", 10)
    assert out["sat_c"].iloc[[0, 1, 4, 5]].eq(13.0).all()
    assert out["sat_c"].iloc[[2, 3]].gt(13.0).all()


def test_stuck_valve_nearly_closed_warms_the_air_and_saturates_the_command():
    out = _inject(_log(), "chw_valve_stuck", 10)
    # 10% of the wanted 50%: a fifth of the 12 °C of cooling
    assert out["sat_c"].iloc[2] == pytest.approx(25.0 - 12.0 * 10 / 50)
    assert out["chw_valve_cmd_pct"].iloc[2] == 100.0


def test_stuck_damper_moves_mixed_air_to_return_air_and_raises_co2():
    out = _inject(_log(), "oa_damper_stuck", 0)
    assert out["mat_c"].iloc[2] == pytest.approx(24.0)  # mixed air = return air
    assert out["oa_damper_cmd_pct"].iloc[2] == 60.0
    assert out["co2_ppm"].iloc[3] > out["co2_ppm"].iloc[2] >= 800.0


def test_sensor_bias_shows_only_with_the_fan_off():
    on = _inject(_log(fan=1), "sat_sensor_bias", 2.0)
    off = _inject(_log(fan=0), "sat_sensor_bias", 2.0)
    assert on["sat_c"].iloc[2] == 13.0  # the controller keeps the reading on target
    assert on["chw_valve_cmd_pct"].iloc[2] > 50.0  # but the valve works harder
    assert off["sat_c"].iloc[2] == 15.0


def test_weak_coil_opens_the_valve_then_warms_the_air():
    half = _inject(_log(), "low_coil_capacity", 50)
    assert half["chw_valve_cmd_pct"].iloc[2] == 100.0  # 50% needed twice: just at the limit
    assert half["sat_c"].iloc[2] == 13.0
    weak = _inject(_log(), "low_coil_capacity", 25)
    assert weak["sat_c"].iloc[2] == pytest.approx(25.0 - 12.0 * 100 / 200)


def test_normal_leaves_the_data_unchanged_and_unknown_fails():
    df = _log()
    assert _inject(df, "normal", 0).equals(df)
    with pytest.raises(ValueError):
        _inject(df, "broken_fan", 1)


def test_keeps_the_column_types_of_the_real_data():
    # The real data is float32; pandas refuses to write float64 values into it silently
    df = _log().astype({c: "float32" for c in ["sat_c", "mat_c", "chw_valve_cmd_pct", "co2_ppm"]})
    for fault, size in [
        ("chw_valve_stuck", 10),
        ("oa_damper_stuck", 0),
        ("sat_sensor_bias", 2.0),
        ("low_coil_capacity", 25),
    ]:
        out = _inject(df, fault, size)
        assert out["co2_ppm"].dtype == "float32"
        assert out["sat_c"].dtype == "float32"
