"""Small helpers used by the EDA notebooks."""

import pandas as pd

from ahu_fdd.config import NORMAL, SAMPLING


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


def gap_blocks(df: pd.DataFrame) -> pd.DataFrame:
    """One row per run of missing 5-minute slots in each AHU: first and last slot, length."""
    step = pd.Timedelta(SAMPLING)
    every_slot = pd.date_range(df["timestamp"].min(), df["timestamp"].max(), freq=step)
    blocks = []
    for ahu_id, rows in df.groupby("ahu_id"):
        missing = pd.Series(every_slot.difference(rows["timestamp"]))
        # A new block starts when a missing slot does not follow the previous one
        block_id = (missing.diff() != step).cumsum()
        runs = missing.groupby(block_id).agg(start="min", end="max", slots="size")
        blocks.append(runs.assign(ahu_id=ahu_id))
    out = pd.concat(blocks, ignore_index=True)
    out["hours"] = out["slots"] * step / pd.Timedelta("1h")
    return out[["ahu_id", "start", "end", "slots", "hours"]]


def longest_runs(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Longest run of exactly the same value for each AHU and sensor: start, end and hours."""
    step = pd.Timedelta(SAMPLING)
    rows = []
    for ahu_id, ahu in df.groupby("ahu_id"):
        for col in columns:
            # A NaN doesn't break a run: compare each row with the last known value
            value = ahu[col].ffill()
            if value.isna().all():
                continue  # this AHU has no such sensor
            run_id = (value != value.shift()).cumsum()
            longest = run_id.value_counts().idxmax()
            run = ahu.loc[run_id == longest, "timestamp"]
            rows.append(
                {
                    "ahu_id": ahu_id,
                    "sensor": col,
                    "start": run.min(),
                    "end": run.max(),
                    "hours": len(run) * step / pd.Timedelta("1h"),
                    "value": value[run_id == longest].iloc[0],
                }
            )
    return pd.DataFrame(rows)


def event_vs_normal(df: pd.DataFrame, labels: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """For each fault event: median of each column during the event minus its AHU normal median.

    Expects a 'label' column (from label_rows). Pass only the rows you want to compare,
    for example fan on and after start-up.
    """
    rows = []
    for event in labels.itertuples():
        ahu = df[df["ahu_id"] == event.ahu_id]
        in_event = (ahu["timestamp"] >= event.start) & (ahu["timestamp"] < event.end)
        normal = ahu[ahu["label"] == NORMAL]
        change = ahu.loc[in_event, columns].median() - normal[columns].median()
        rows.append(
            {
                "event": event.Index,
                "ahu_id": event.ahu_id,
                "fault_type": event.fault_type,
                "rows": int(in_event.sum()),
                **change.to_dict(),
            }
        )
    return pd.DataFrame(rows).set_index("event")
