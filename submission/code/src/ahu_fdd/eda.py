"""Small helpers used by the EDA notebooks."""

import pandas as pd

from ahu_fdd.config import SAMPLING


def expected_slots(start: pd.Timestamp, end: pd.Timestamp) -> int:
    """Number of 5-minute slots between two timestamps, both included."""
    return int((end - start) / pd.Timedelta(SAMPLING)) + 1


def coverage_per_ahu(df: pd.DataFrame) -> pd.DataFrame:
    """Rows, duplicates and missing 5-minute slots for each AHU of a sensor log."""
    expected = expected_slots(df["timestamp"].min(), df["timestamp"].max())
    cov = df.groupby("ahu_id").agg(rows=("timestamp", "size"), unique=("timestamp", "nunique"))
    # A duplicate is an extra row for a timestamp that already exists
    cov["duplicates"] = cov["rows"] - cov["unique"]
    # A missing slot is a 5-minute timestamp with no row at all
    cov["missing"] = expected - cov["unique"]
    cov["missing_pct"] = (100 * cov["missing"] / expected).round(2)
    return cov


def fan_on_hours_per_event(df: pd.DataFrame, labels: pd.DataFrame) -> pd.Series:
    """Hours with the fan on during each fault event (only these rows are scored)."""
    hours = []
    for event in labels.itertuples(index=False):
        in_event = (
            (df["ahu_id"] == event.ahu_id)
            & (df["timestamp"] >= event.start)
            & (df["timestamp"] < event.end)
        )
        fan_on_rows = (df.loc[in_event, "fan_status"] == 1).sum()
        hours.append(fan_on_rows * pd.Timedelta(SAMPLING) / pd.Timedelta("1h"))
    return pd.Series(hours, index=labels.index, name="fan_on_hours")


def coverage_by_building(cov: pd.DataFrame) -> pd.DataFrame:
    """Summarise coverage_per_ahu() by building, so the differences between buildings stand out."""
    cov = cov.assign(building=cov.index.str[:2])
    return (
        cov.groupby("building")
        .agg(
            machines=("rows", "size"),
            machines_with_duplicates=("duplicates", lambda d: int((d > 0).sum())),
            duplicates_max=("duplicates", "max"),
            missing_pct_avg=("missing_pct", "mean"),
            missing_pct_max=("missing_pct", "max"),
        )
        .round(2)
    )
