"""Load the raw data files."""

import pandas as pd

from ahu_fdd.config import PATHS, Paths


def load_sensors(split: str, *, paths: Paths = PATHS) -> pd.DataFrame:
    """Load the sensor log for 'train' or 'test', sorted by AHU and time."""
    if split not in ("train", "test"):
        raise ValueError(f"split must be 'train' or 'test', got {split!r}")
    df = pd.read_parquet(paths.train if split == "train" else paths.test)
    return df.sort_values(["ahu_id", "timestamp"], ignore_index=True)


def load_labels(*, paths: Paths = PATHS) -> pd.DataFrame:
    """Load the fault events table (one row per event)."""
    return pd.read_csv(paths.labels, parse_dates=["start", "end"])


def load_metadata(*, paths: Paths = PATHS) -> pd.DataFrame:
    """Load the AHU metadata (one row per AHU)."""
    return pd.read_csv(paths.metadata)
