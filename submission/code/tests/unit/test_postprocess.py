import pandas as pd

from ahu_fdd.postprocess import drop_short_alarms


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
