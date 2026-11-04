"""Load the raw data files, add the basic columns every notebook needs and clean them."""

import pandas as pd

from ahu_fdd.config import (
    CLOCK_SHIFT_BUILDING,
    CLOCK_SHIFT_END,
    CLOCK_SHIFT_OFFSET,
    CLOCK_SHIFT_START,
    CO2_LIMITS,
    FROZEN_MIN_HOURS,
    FROZEN_SENSORS,
    NORMAL,
    PATHS,
    POWER_IN_WATTS_AHU,
    POWER_IN_WATTS_END,
    POWER_IN_WATTS_START,
    SAMPLING,
    Paths,
)


def load_sensors(split: str, *, paths: Paths = PATHS) -> pd.DataFrame:
    """Load the sensor log ("diary") for 'train' or 'test', sorted by AHU and time."""
    if split not in ("train", "test"):
        raise ValueError(f"split must be 'train' or 'test', got {split!r}")
    df = pd.read_parquet(paths.train if split == "train" else paths.test)
    # Sorting by AHU and time makes every later step (gaps, rolling windows) simpler.
    # A stable sort keeps the file order of duplicate stamps, which fix_clock_shift needs.
    return df.sort_values(["ahu_id", "timestamp"], kind="stable", ignore_index=True)


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


def fix_clock_shift(
    df: pd.DataFrame,
    *,
    building: str = CLOCK_SHIFT_BUILDING,
    start: str = CLOCK_SHIFT_START,
    end: str = CLOCK_SHIFT_END,
    offset: str = CLOCK_SHIFT_OFFSET,
) -> pd.DataFrame:
    """Move the rows of a block saved with an early clock to their real time.

    Expects df sorted by ahu_id and timestamp with a stable sort (as load_sensors does).
    """
    start, end, offset = pd.Timestamp(start), pd.Timestamp(end), pd.Timedelta(offset)
    ts = df["timestamp"]
    in_block = df["ahu_id"].str.startswith(building) & (ts >= start) & (ts < end)

    # In the first hours of the block (as long as the offset) each stamp usually exists twice:
    # the real row of that time comes first in the file, the early-clock row second
    in_overlap = in_block & (ts < start + offset)
    copies = df.groupby(["ahu_id", "timestamp"])["timestamp"].transform("size")
    copy_number = df.groupby(["ahu_id", "timestamp"]).cumcount()

    # If a stamp in the overlap has only one row, I can't tell which clock it belongs to: drop it
    ambiguous = in_overlap & (copies == 1)
    to_move = in_block & (~in_overlap | (copy_number == 1))

    out = df.copy()
    out.loc[to_move, "timestamp"] = ts[to_move] + offset
    out = out[~ambiguous]
    return out.sort_values(["ahu_id", "timestamp"], kind="stable", ignore_index=True)


def merge_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Keep one row per AHU and timestamp, filling a null in one copy with the other copy.

    Run it after fix_clock_shift: before that, the office duplicates are different hours.
    """
    # first() takes, for each column, the first value that is not null among the copies
    out = df.groupby(["ahu_id", "timestamp"], as_index=False, sort=True).first()
    return out[df.columns]


def fix_power_units(
    df: pd.DataFrame,
    *,
    ahu_id: str = POWER_IN_WATTS_AHU,
    start: str = POWER_IN_WATTS_START,
    end: str = POWER_IN_WATTS_END,
) -> pd.DataFrame:
    """Convert fan power from watts to kW for the rows of one AHU that were logged in watts."""
    ts = df["timestamp"]
    in_watts = (df["ahu_id"] == ahu_id) & (ts >= pd.Timestamp(start)) & (ts < pd.Timestamp(end))
    out = df.copy()
    out.loc[in_watts, "fan_power_kw"] = out.loc[in_watts, "fan_power_kw"] / 1000
    return out


def blank_co2_limits(df: pd.DataFrame, *, limits: tuple[float, float] = CO2_LIMITS) -> pd.DataFrame:
    """Set to NaN the CO2 readings stuck at the sensor limits (glitches, not real values)."""
    low, high = limits
    out = df.copy()
    at_limit = (out["co2_ppm"] <= low) | (out["co2_ppm"] >= high)
    out.loc[at_limit, "co2_ppm"] = float("nan")
    return out


def blank_frozen(
    df: pd.DataFrame,
    *,
    columns: tuple[str, ...] = FROZEN_SENSORS,
    min_hours: float = FROZEN_MIN_HOURS,
) -> pd.DataFrame:
    """Set to NaN the readings of a sensor that stays at exactly the same value for min_hours.

    Expects df sorted by ahu_id and timestamp.
    """
    min_rows = int(pd.Timedelta(hours=min_hours) / pd.Timedelta(SAMPLING))
    new_ahu = df["ahu_id"] != df["ahu_id"].shift()
    out = df.copy()
    for col in columns:
        # A NaN doesn't break a run: compare each row with the last known value
        value = out[col].ffill()
        # A new run starts when the value changes or a new AHU starts
        run_id = (new_ahu | (value != value.shift())).cumsum()
        run_rows = run_id.groupby(run_id).transform("size")
        out.loc[run_rows >= min_rows, col] = float("nan")
    return out


def clean_sensors(df: pd.DataFrame) -> pd.DataFrame:
    """Run every cleaning step in the right order (the clock fix must come before the merge)."""
    df = fix_clock_shift(df)
    df = merge_duplicates(df)
    df = fix_power_units(df)
    df = blank_co2_limits(df)
    return blank_frozen(df)
