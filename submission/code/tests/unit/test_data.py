import pandas as pd
import pytest

from ahu_fdd.config import FAULT_TYPES, PATHS, Paths
from ahu_fdd.data import label_rows, load_labels, load_metadata, load_sensors


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
