import pandas as pd

from ahu_fdd.features import minutes_since_fan_on


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
