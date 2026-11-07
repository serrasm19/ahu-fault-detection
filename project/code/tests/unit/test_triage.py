import pandas as pd
import pytest

from ahu_fdd.config import Paths
from ahu_fdd.triage import alarm_evidence, list_alarms, load_ahu


def _rows(n=24, **changes):
    """One AHU with its normal, running after start-up: small changes make each fault."""
    rows = pd.DataFrame(
        {
            "ahu_id": "B1-AHU-01",
            "timestamp": pd.date_range("2025-03-10 08:00", periods=n, freq="5min"),
            "label": "normal",
            "fan_status": 1,
            "minutes_on": 60.0,
            "sat_c": 13.0,
            "mat_c": 25.0,
            "rat_c": 24.0,
            "oat_c": 30.0,
            "chwst_c": 7.0,
            "co2_ppm": 800.0,
            "oat_change_1h": -0.5,
            "rest_offset": float("nan"),
            "last_rest_offset": -0.5,
            "sat_error_run": 0.0,
            "chw_valve_cmd_pct_run": 50.0,
            "oa_damper_cmd_pct": 20.0,
            "oa_fraction_run": 0.15,
            "valve_excess": 0.0,
            "sat_error_dev": 0.0,
            "valve_at_limit_1h": 0.0,
            "oa_fraction_dev": 0.0,
            "oa_fraction_1h": 0.15,
            "rest_offset_dev": 0.0,
            "base_sat_error": 0.0,
            "base_chw_valve_cmd_pct": 50.0,
            "base_oa_fraction": 0.15,
            "base_oa_damper_cmd_pct": 20.0,
            "base_co2_ppm": 800.0,
            "base_rest_offset": -0.5,
        }
    )
    return rows.assign(**changes)


def _evidence(rows):
    return alarm_evidence(rows, start="2025-03-10", end="2025-03-11")


def test_a_healthy_window_fires_no_rule():
    evidence = _evidence(_rows())
    assert evidence["main_rule_type"] == "normal"
    assert all(rule["share_of_running_rows"] == 0 for rule in evidence["rules"])


def test_a_stuck_flap_comes_first_with_its_signals():
    evidence = _evidence(
        _rows(oa_fraction_dev=-0.14, oa_fraction_1h=0.01, oa_fraction_run=0.01, co2_ppm=1500.0)
    )
    assert evidence["main_rule_type"] == "oa_damper_stuck"
    assert evidence["rules"][0]["plain_name"] == "stuck flap"
    assert evidence["rules"][0]["share_of_running_rows"] == 1.0
    assert evidence["signals"]["co2_ppm"] == {"window": 1500.0, "normal": 800.0, "change": 700.0}
    assert evidence["context"]["outdoor_minus_return_c"] == 6.0


def test_start_up_rows_are_left_out():
    rows = _rows(oa_fraction_dev=-0.14, oa_fraction_1h=0.01, minutes_on=10.0)
    evidence = _evidence(rows)
    assert evidence["rows"] == {"window": 24, "running": 0, "fan_on_share": 1.0}
    assert evidence["main_rule_type"] == "normal"
    assert evidence["signals"]["co2_ppm"]["window"] is None


def test_machine_always_at_its_limit_shows_in_the_context():
    healthy = _rows(chw_valve_cmd_pct_run=100.0)
    assert _evidence(healthy)["context"]["valve_at_limit_share_when_healthy"] == 1.0


def test_no_co2_sensor_gives_empty_values():
    evidence = _evidence(_rows(co2_ppm=float("nan"), base_co2_ppm=float("nan")))
    assert evidence["context"]["has_co2_sensor"] is False
    assert evidence["signals"]["co2_ppm"]["change"] is None


def test_empty_window_is_an_error():
    with pytest.raises(ValueError, match="no rows"):
        alarm_evidence(_rows(), start="2026-01-01", end="2026-01-02")


def _write_test_period(folder):
    """A small test file and predictions: 3 fan-on fault rows of one AHU."""
    stamps = pd.date_range("2025-07-01 08:00", periods=5, freq="5min")
    sensors = pd.DataFrame({"ahu_id": "B1-AHU-01", "timestamp": stamps, "fan_status": 1})
    sensors.to_parquet(folder / "ahu_test.parquet")
    sensors.to_parquet(folder / "ahu_train.parquet")
    faults = ["normal", "oa_damper_stuck", "oa_damper_stuck", "oa_damper_stuck", "normal"]
    pred = sensors[["ahu_id", "timestamp"]].assign(fault_type=faults)
    pred.to_csv(folder / "predictions.csv", index=False)
    return Paths(data_dir=folder, output_dir=folder)


def test_list_alarms_joins_rows_into_alarms(tmp_path):
    alarms = list_alarms(paths=_write_test_period(tmp_path))
    assert len(alarms) == 1
    assert alarms.loc[0, "rows"] == 3
    assert alarms.loc[0, "plain_name"] == "stuck flap"


def test_load_ahu_refuses_an_unknown_machine(tmp_path):
    with pytest.raises(ValueError, match="unknown AHU"):
        load_ahu("B9-AHU-99", paths=_write_test_period(tmp_path))
