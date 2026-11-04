import pandas as pd
import pytest

from ahu_fdd.data import add_building
from ahu_fdd.eda import (
    coverage_by_building,
    coverage_per_ahu,
    event_vs_normal,
    expected_slots,
    fan_on_hours_per_event,
    gap_blocks,
    longest_runs,
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


def test_gap_blocks_groups_consecutive_missing_slots():
    # AHU-01 misses 00:05 alone and 00:20-00:25 together. AHU-02 has every slot.
    day = "2025-03-10 "
    a = _log("B2-AHU-01", [day + t for t in ["00:00", "00:10", "00:15", "00:30"]])
    b = _log(
        "B2-AHU-02",
        [day + t for t in ["00:00", "00:05", "00:10", "00:15", "00:20", "00:25", "00:30"]],
    )
    gaps = gap_blocks(pd.concat([a, b]))
    assert gaps["ahu_id"].tolist() == ["B2-AHU-01", "B2-AHU-01"]
    assert gaps["slots"].tolist() == [1, 2]
    assert gaps["start"].dt.strftime("%H:%M").tolist() == ["00:05", "00:20"]
    assert gaps["end"].dt.strftime("%H:%M").tolist() == ["00:05", "00:25"]
    assert gaps["hours"].tolist() == [5 / 60, 10 / 60]


def test_longest_runs_finds_the_longest_flat_stretch():
    df = pd.DataFrame(
        {
            "ahu_id": ["B1-AHU-07"] * 5,
            "timestamp": pd.date_range("2025-05-05", periods=5, freq="5min"),
            "rat_c": [22.0, 23.4, 23.4, None, 23.4],
            "co2_ppm": [None] * 5,  # sensor not installed: skipped
        }
    )
    runs = longest_runs(df, ["rat_c", "co2_ppm"])
    assert runs["sensor"].tolist() == ["rat_c"]
    assert runs["hours"].iloc[0] == 4 * 5 / 60
    assert runs["value"].iloc[0] == 23.4
    assert runs["start"].iloc[0] == pd.Timestamp("2025-05-05 00:05")


def test_event_vs_normal_compares_with_the_same_ahu():
    df = pd.DataFrame(
        {
            "ahu_id": ["B1-AHU-01"] * 4 + ["B1-AHU-02"] * 2,
            "timestamp": pd.date_range("2025-02-10", periods=6, freq="h"),
            "oaf": [0.2, 0.2, 0.0, 0.0, 0.5, 0.5],
            "label": ["normal", "normal", "oa_damper_stuck", "oa_damper_stuck", "normal", "normal"],
        }
    )
    labels = pd.DataFrame(
        {
            "ahu_id": ["B1-AHU-01"],
            "fault_type": ["oa_damper_stuck"],
            "start": [pd.Timestamp("2025-02-10 02:00")],
            "end": [pd.Timestamp("2025-02-10 04:00")],
        }
    )
    out = event_vs_normal(df, labels, ["oaf"])
    # 0.0 during the event vs 0.2 normal for B1-AHU-01 (B1-AHU-02 is not used)
    assert out.loc[0, "oaf"] == pytest.approx(-0.2)
    assert out.loc[0, "rows"] == 2
