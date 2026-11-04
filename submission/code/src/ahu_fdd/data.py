"""Load the raw data files and add the basic columns every notebook needs."""

import pandas as pd

from ahu_fdd.config import NORMAL, PATHS, Paths


def load_sensors(split: str, *, paths: Paths = PATHS) -> pd.DataFrame:
    """Load the sensor log ("diary") for 'train' or 'test', sorted by AHU and time."""
    if split not in ("train", "test"):
        raise ValueError(f"split must be 'train' or 'test', got {split!r}")
    df = pd.read_parquet(paths.train if split == "train" else paths.test)
    # Sorting by AHU and time makes every later step (gaps, rolling windows) simpler
    return df.sort_values(["ahu_id", "timestamp"], ignore_index=True)


def load_labels(*, paths: Paths = PATHS) -> pd.DataFrame:
    """Load the fault events ("repair reports"), one row per event."""
    return pd.read_csv(paths.labels, parse_dates=["start", "end"])


def load_metadata(*, paths: Paths = PATHS) -> pd.DataFrame:
    """Load the AHU metadata ("ID cards"), one row per AHU."""
    return pd.read_csv(paths.metadata)


def add_building(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'building' column (B1, B2, B3) taken from the first two letters of ahu_id."""
    df["building"] = df["ahu_id"].str[:2]
    return df


def label_rows(df: pd.DataFrame, labels: pd.DataFrame) -> pd.Series:
    """Fault type for each row if it falls in [start, end) of an event of its AHU, else normal."""
    # Start with every row as normal, then "paint" the rows inside each event
    out = pd.Series(NORMAL, index=df.index, dtype=object)
    for event in labels.itertuples(index=False):
        in_event = (
            (df["ahu_id"] == event.ahu_id)
            & (df["timestamp"] >= event.start)
            & (df["timestamp"] < event.end)  # end is the repair time, so it is not included
        )
        out[in_event] = event.fault_type
    return out
