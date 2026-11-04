import pandas as pd
import pytest

from ahu_fdd.config import FAULT_TYPES, PATHS, Paths
from ahu_fdd.data import (
    blank_co2_limits,
    blank_frozen,
    clean_sensors,
    fix_clock_shift,
    fix_power_units,
    label_rows,
    load_labels,
    load_metadata,
    load_sensors,
    merge_duplicates,
)


@pytest.fixture
def fake_paths(tmp_path):
    """Write tiny versions of the four data files and return paths to them."""
    sensors = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2025-01-01 00:05", "2025-01-01 00:00", "2025-01-01 00:00"]
            ),
            "ahu_id": ["B1-AHU-01", "B1-AHU-01", "B1-AHU-02"],
            "sat_c": [13.1, 13.0, 14.0],
        }
    )
    sensors.to_parquet(tmp_path / "ahu_train.parquet")
    sensors.to_parquet(tmp_path / "ahu_test.parquet")
    pd.DataFrame(
        {
            "ahu_id": ["B1-AHU-01"],
            "fault_type": ["chw_valve_stuck"],
            "start": ["2025-01-01 00:00:00"],
            "end": ["2025-01-02 00:00:00"],
        }
    ).to_csv(tmp_path / "fault_labels_train.csv", index=False)
    pd.DataFrame({"ahu_id": ["B1-AHU-01", "B1-AHU-02"], "building": ["B1", "B1"]}).to_csv(
        tmp_path / "ahu_metadata.csv", index=False
    )
    return Paths(data_dir=tmp_path, output_dir=tmp_path)


def test_load_sensors_sorts_by_ahu_and_time(fake_paths):
    df = load_sensors("train", paths=fake_paths)
    assert list(df["ahu_id"]) == ["B1-AHU-01", "B1-AHU-01", "B1-AHU-02"]
    assert df["timestamp"].iloc[0] < df["timestamp"].iloc[1]
    assert df.index.tolist() == [0, 1, 2]


def test_load_sensors_reads_test_split(fake_paths):
    assert len(load_sensors("test", paths=fake_paths)) == 3


def test_load_sensors_rejects_unknown_split(fake_paths):
    with pytest.raises(ValueError):
        load_sensors("validation", paths=fake_paths)


def test_load_labels_parses_dates(fake_paths):
    labels = load_labels(paths=fake_paths)
    assert pd.api.types.is_datetime64_any_dtype(labels["start"])
    assert pd.api.types.is_datetime64_any_dtype(labels["end"])


def test_load_metadata_returns_one_row_per_ahu(fake_paths):
    meta = load_metadata(paths=fake_paths)
    assert meta["ahu_id"].is_unique


def test_predictions_path_is_in_output_dir(fake_paths):
    assert fake_paths.predictions == fake_paths.output_dir / "predictions.csv"


@pytest.mark.skipif(not PATHS.data_dir.exists(), reason="real data not available (e.g. in CI)")
def test_real_labels_and_metadata_are_consistent():
    labels = load_labels()
    meta = load_metadata()
    assert set(labels["fault_type"]) <= set(FAULT_TYPES)
    assert (labels["end"] > labels["start"]).all()
    assert set(labels["ahu_id"]) <= set(meta["ahu_id"])
    assert len(meta) == 40


def test_label_rows_marks_only_rows_inside_the_event():
    df = pd.DataFrame(
        {
            "ahu_id": ["B1-AHU-01"] * 3 + ["B1-AHU-02"],
            "timestamp": pd.to_datetime(
                ["2025-01-01 00:00", "2025-01-01 00:05", "2025-01-01 00:10", "2025-01-01 00:05"]
            ),
        }
    )
    labels = pd.DataFrame(
        {
            "ahu_id": ["B1-AHU-01"],
            "fault_type": ["oa_damper_stuck"],
            "start": pd.to_datetime(["2025-01-01 00:05"]),
            "end": pd.to_datetime(["2025-01-01 00:10"]),
        }
    )
    # end is exclusive and other AHUs are not touched
    assert label_rows(df, labels).tolist() == ["normal", "oa_damper_stuck", "normal", "normal"]


def test_fix_clock_shift_moves_only_the_early_rows():
    # Block stamped 00:00 to 00:20 with a 10 minute offset. 00:00 and 00:05 are in the overlap,
    # so they appear twice: real row first, early-clock row second.
    stamps = ["00:00", "00:00", "00:05", "00:05", "00:10", "00:15", "00:30"]
    df = pd.DataFrame(
        {
            "ahu_id": ["B1-AHU-01"] * len(stamps) + ["B3-AHU-01"],
            "timestamp": pd.to_datetime([f"2025-06-01 {s}" for s in stamps + ["00:10"]]),
            "value": ["real", "early", "real", "early", "early", "early", "real", "mall"],
        }
    )
    out = fix_clock_shift(
        df, building="B1", start="2025-06-01 00:00", end="2025-06-01 00:20", offset="10min"
    )
    b1 = out[out["ahu_id"] == "B1-AHU-01"]

    # Every stamp is now unique and the hole at 00:20 and 00:25 is filled
    assert b1["timestamp"].is_unique
    assert b1["timestamp"].dt.strftime("%H:%M").tolist() == [
        "00:00",
        "00:05",
        "00:10",
        "00:15",
        "00:20",
        "00:25",
        "00:30",
    ]
    assert b1["value"].tolist() == ["real", "real", "early", "early", "early", "early", "real"]
    # Other buildings are not touched
    assert out.loc[out["ahu_id"] == "B3-AHU-01", "timestamp"].tolist() == [
        pd.Timestamp("2025-06-01 00:10")
    ]


def test_fix_clock_shift_drops_single_rows_in_the_overlap():
    # 00:05 has only one row inside the overlap, so its clock is unknown and it is dropped
    stamps = ["00:00", "00:00", "00:05", "00:10"]
    df = pd.DataFrame(
        {
            "ahu_id": ["B1-AHU-01"] * len(stamps),
            "timestamp": pd.to_datetime([f"2025-06-01 {s}" for s in stamps]),
            "value": ["real", "early", "unknown", "early"],
        }
    )
    out = fix_clock_shift(
        df, building="B1", start="2025-06-01 00:00", end="2025-06-01 00:20", offset="10min"
    )
    assert out["value"].tolist() == ["real", "early", "early"]
    assert out["timestamp"].dt.strftime("%H:%M").tolist() == ["00:00", "00:10", "00:20"]


def test_merge_duplicates_keeps_one_row_and_fills_nulls():
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2025-02-14 00:00"] * 2 + ["2025-02-14 00:05"]),
            "ahu_id": ["B3-AHU-01"] * 3,
            "sat_c": [None, 13.0, 13.2],
            "mat_c": [24.0, None, 24.1],
        }
    )
    out = merge_duplicates(df)
    # One row per stamp, the nulls of each copy filled by the other, columns in the same order
    assert out["timestamp"].is_unique
    assert out["sat_c"].tolist() == [13.0, 13.2]
    assert out["mat_c"].tolist() == [24.0, 24.1]
    assert list(out.columns) == list(df.columns)


def test_fix_power_units_only_touches_the_window_of_that_ahu():
    df = pd.DataFrame(
        {
            "ahu_id": ["B3-AHU-04", "B3-AHU-04", "B3-AHU-04", "B3-AHU-05"],
            "timestamp": pd.to_datetime(
                ["2025-03-31 23:55", "2025-04-01 00:00", "2025-04-22 00:00", "2025-04-01 00:00"]
            ),
            "fan_power_kw": [6.0, 6000.0, 6.0, 6.0],
        }
    )
    out = fix_power_units(df, ahu_id="B3-AHU-04", start="2025-04-01", end="2025-04-22")
    assert out["fan_power_kw"].tolist() == [6.0, 6.0, 6.0, 6.0]


def test_blank_co2_limits_removes_only_values_at_the_limits():
    df = pd.DataFrame({"co2_ppm": [0.0, 650.0, 5000.0, None]})
    out = blank_co2_limits(df, limits=(0, 5000))
    assert out["co2_ppm"].isna().tolist() == [True, False, True, True]


def test_blank_frozen_blanks_long_runs_only():
    # AHU-01: 20.0 for 4 rows (20 minutes, with a NaN inside), then it moves. min_hours = 15 min
    df = pd.DataFrame(
        {
            "ahu_id": ["B1-AHU-01"] * 6 + ["B1-AHU-02"] * 2,
            "timestamp": pd.date_range("2025-05-05", periods=8, freq="5min"),
            "rat_c": [20.0, 20.0, None, 20.0, 21.0, 22.0, 20.0, 20.0],
        }
    )
    out = blank_frozen(df, columns=("rat_c",), min_hours=0.25)
    # The run of AHU-01 is blanked; the short run of AHU-02 stays (a new AHU starts a new run)
    assert out["rat_c"].isna().tolist() == [True, True, True, True, False, False, False, False]


def test_clean_sensors_runs_all_steps():
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2025-02-14 00:00"] * 2),
            "ahu_id": ["B2-AHU-03"] * 2,
            "fan_power_kw": [5.0, 5.0],
            "co2_ppm": [5000.0, 5000.0],
            "sat_c": [13.0, None],
            "mat_c": [24.0, 24.0],
            "rat_c": [24.5, 24.5],
            "oat_c": [28.0, 28.0],
            "chwst_c": [7.0, 7.0],
        }
    )
    out = clean_sensors(df)
    assert len(out) == 1
    assert out["co2_ppm"].isna().all()
