import pandas as pd

from ahu_fdd import simulation
from ahu_fdd.config import SENSITIVITY_FAULT_DAYS, SENSITIVITY_LEAD_DAYS


class _Fitted:
    """A stand-in for the trained pipeline: only what simulate() touches."""

    model = None
    features: list[str] = []

    @staticmethod
    def deviations(df):
        return df


def _data():
    """16 days of one running AHU, one row per hour."""
    stamps = pd.date_range("2025-07-05", periods=16 * 24, freq="h")
    return pd.DataFrame({"ahu_id": "B1-AHU-01", "timestamp": stamps, "fan_status": 1})


def _simulate(monkeypatch, alarm_from=None, alarm_to=None):
    """Run simulate() with a fixed alarm, so only its scoring is tested."""

    def alarms(fitted, target, **settings):
        pred = pd.Series("normal", index=target.index, dtype=object)
        if alarm_from:
            inside = target["timestamp"].between(alarm_from, alarm_to)
            pred[inside] = "oa_damper_stuck"
        return pred

    monkeypatch.setattr(simulation, "predict_alarms", alarms)
    monkeypatch.setattr(simulation, "add_features", lambda df: df.assign(minutes_on=60.0))
    monkeypatch.setattr(simulation, "inject_fault", lambda df, **kwargs: df)
    monkeypatch.setattr(
        simulation,
        "fault_proba",
        lambda model, df, features: pd.DataFrame({"normal": 1.0}, index=df.index),
    )
    return simulation.simulate(
        _Fitted(),
        _data(),
        ahu_id="B1-AHU-01",
        window_start=pd.Timestamp("2025-07-07"),
        fault="oa_damper_stuck",
        fault_start=pd.Timestamp("2025-07-10"),
        fault_end=pd.Timestamp("2025-07-17"),
        size=0,
        min_prob=0.8,
        min_alarm_rows=24,
        max_gap_rows=72,
    )


def test_simulate_scores_a_detected_fault(monkeypatch):
    result = _simulate(monkeypatch, "2025-07-10 08:00", "2025-07-11 08:00")
    assert result.detected
    assert result.delay_h == 8
    assert result.main_type == "oa_damper_stuck"
    assert result.false_alarms == 0


def test_simulate_counts_an_alarm_before_the_fault_as_false(monkeypatch):
    result = _simulate(monkeypatch, "2025-07-08 08:00", "2025-07-08 12:00")
    assert not result.detected
    assert result.delay_h is None
    assert result.false_alarms == 1


def _fake_simulate(monkeypatch):
    """Record each call, and detect only sizes of 2 or more."""
    calls = []

    def fake(fitted, data, **kwargs):
        calls.append(kwargs)
        found = kwargs["fault"] != "normal" and kwargs["size"] >= 2
        return simulation.SimulationResult(
            before=None,
            after=None,
            fault_probability=None,
            events=None,
            detected=found,
            delay_h=5.0 if found else None,
            main_type=kwargs["fault"] if found else None,
            false_alarms=0,
        )

    monkeypatch.setattr(simulation, "simulate", fake)
    return calls


def test_sensitivity_table_starts_with_a_control_and_keeps_the_size_order(monkeypatch):
    calls = _fake_simulate(monkeypatch)
    table = simulation.sensitivity_table(
        _Fitted(),
        _data(),
        ahu_id="B1-AHU-01",
        fault="sat_sensor_bias",
        window_start=pd.Timestamp("2025-07-07"),
        sizes=(1.0, 2.0, 3.0),
    )
    assert table["fault"].tolist() == ["normal", *["sat_sensor_bias"] * 3]
    assert table["detected"].tolist() == [False, False, True, True]
    assert table["right_type"].tolist() == [False, False, True, True]
    assert pd.isna(table.loc[0, "size"])
    start, end = calls[0]["fault_start"], calls[0]["fault_end"]
    assert start == pd.Timestamp("2025-07-07") + pd.Timedelta(days=SENSITIVITY_LEAD_DAYS)
    assert end - start == pd.Timedelta(days=SENSITIVITY_FAULT_DAYS)


def test_sensitivity_table_uses_the_sizes_in_config_by_default(monkeypatch):
    _fake_simulate(monkeypatch)
    table = simulation.sensitivity_table(
        _Fitted(),
        _data(),
        ahu_id="B1-AHU-01",
        fault="sat_sensor_bias",
        window_start=pd.Timestamp("2025-07-07"),
    )
    assert table["size"].dropna().tolist() == [0.5, 1.0, 1.5, 2.0, 3.0]
