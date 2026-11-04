import pandas as pd
import pytest

from ahu_fdd.evaluation import month_folds, rows_to_events, score_events


def _rows(preds, fan=None, ahu="B3-AHU-01", start="2025-03-10 09:00"):
    n = len(preds)
    return pd.DataFrame(
        {
            "ahu_id": ahu,
            "timestamp": pd.date_range(start, periods=n, freq="h"),
            "fan_status": fan if fan is not None else [1] * n,
            "pred": preds,
        }
    )


def test_rows_to_events_skips_fan_off_rows_and_splits_on_label_change():
    # A fault, a fan-off row in the middle (ignored), then a different fault
    df = _rows(
        ["normal", "chw_valve_stuck", "normal", "chw_valve_stuck", "low_coil_capacity"],
        fan=[1, 1, 0, 1, 1],
    )
    events = rows_to_events(df)
    assert events["fault_type"].tolist() == ["chw_valve_stuck", "low_coil_capacity"]
    assert events["rows"].tolist() == [2, 1]


def test_score_events_detection_delay_type_and_false_alarms():
    # True event from 11:00 to 15:00. Detected at 12:00 with the right type.
    # A separate predicted event at 18:00 touches no true event: one false alarm.
    preds = ["normal"] * 3 + ["oa_damper_stuck"] * 3 + ["normal"] * 3 + ["sat_sensor_bias"]
    df = _rows(preds)
    labels = pd.DataFrame(
        {
            "ahu_id": ["B3-AHU-01"],
            "fault_type": ["oa_damper_stuck"],
            "start": [pd.Timestamp("2025-03-10 11:00")],
            "end": [pd.Timestamp("2025-03-10 15:00")],
        }
    )
    score = score_events(df, labels)
    assert score["detected"] == 1.0
    assert score["type_right"] == 1.0
    assert score["median_delay_h"] == pytest.approx(1.0)
    assert score["false_alarms"] == 1


def test_score_events_counts_a_missed_event():
    df = _rows(["normal"] * 5)
    labels = pd.DataFrame(
        {
            "ahu_id": ["B3-AHU-01"],
            "fault_type": ["chw_valve_stuck"],
            "start": [pd.Timestamp("2025-03-10 10:00")],
            "end": [pd.Timestamp("2025-03-10 12:00")],
        }
    )
    score = score_events(df, labels)
    assert score["detected"] == 0.0
    assert score["false_alarms"] == 0


def test_month_folds_cover_each_period_once():
    ts = pd.Series(pd.to_datetime(["2025-01-15", "2025-03-15", "2025-05-15"]))
    folds = month_folds(ts, [("2025-01-01", "2025-03-01"), ("2025-03-01", "2025-07-01")])
    assert [f.tolist() for f in folds] == [[True, False, False], [False, True, True]]
