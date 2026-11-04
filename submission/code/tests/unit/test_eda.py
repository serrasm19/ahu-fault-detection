import pandas as pd

from ahu_fdd.data import add_building
from ahu_fdd.eda import (
    coverage_by_building,
    coverage_per_ahu,
    expected_slots,
    fan_on_hours_per_event,
)


def _log(ahu_id, times, fan=1):
    return pd.DataFrame({"ahu_id": ahu_id, "timestamp": pd.to_datetime(times), "fan_status": fan})


def test_expected_slots_counts_both_ends():
    assert expected_slots(pd.Timestamp("2025-01-01 00:00"), pd.Timestamp("2025-01-01 00:10")) == 3


def test_coverage_finds_duplicates_and_missing_slots():
    # AHU 1: 00:00 twice (duplicate), 00:05 missing. AHU 2: complete
    df = pd.concat(
        [
            _log("B1-AHU-01", ["2025-01-01 00:00", "2025-01-01 00:00", "2025-01-01 00:10"]),
            _log("B1-AHU-02", ["2025-01-01 00:00", "2025-01-01 00:05", "2025-01-01 00:10"]),
        ]
    )
    cov = coverage_per_ahu(df)
    assert cov.loc["B1-AHU-01", ["duplicates", "missing"]].tolist() == [1, 1]
    assert cov.loc["B1-AHU-02", ["duplicates", "missing"]].tolist() == [0, 0]


def test_fan_on_hours_only_counts_rows_with_fan_on_inside_the_event():
    times = pd.date_range("2025-01-01 00:00", periods=24, freq="5min")  # 2 hours
    df = _log("B1-AHU-01", times)
    df.loc[12:, "fan_status"] = 0  # fan off in the second hour
    labels = pd.DataFrame(
        {
            "ahu_id": ["B1-AHU-01"],
            "start": [pd.Timestamp("2025-01-01 00:00")],
            "end": [pd.Timestamp("2025-01-01 02:00")],
        }
    )
    assert fan_on_hours_per_event(df, labels).tolist() == [1.0]


def test_add_building_takes_first_two_letters():
    df = add_building(pd.DataFrame({"ahu_id": ["B2-AHU-07"]}))
    assert df["building"].tolist() == ["B2"]


def test_coverage_by_building_counts_machines_with_duplicates():
    cov = pd.DataFrame(
        {"rows": [4, 4, 4], "duplicates": [1, 0, 2], "missing_pct": [25.0, 0.0, 50.0]},
        index=["B1-AHU-01", "B1-AHU-02", "B3-AHU-01"],
    )
    summary = coverage_by_building(cov)
    assert summary.loc[
        "B1", ["machines", "machines_with_duplicates", "duplicates_max"]
    ].tolist() == [2, 1, 1]
    assert summary.loc["B1", "missing_pct_avg"] == 12.5
    assert summary.loc["B3", "machines_with_duplicates"] == 1
