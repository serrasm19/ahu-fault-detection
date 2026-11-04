"""Features built from the cleaned sensor log."""

import pandas as pd

from ahu_fdd.config import SAMPLING


def minutes_since_fan_on(df: pd.DataFrame) -> pd.Series:
    """Minutes since the fan last started (0 on the first row with the fan on), NaN with fan off.

    Expects df sorted by ahu_id and timestamp.
    """
    # A new "stretch" starts when the AHU changes or the fan status changes
    new_stretch = (df["ahu_id"] != df["ahu_id"].shift()) | (
        df["fan_status"] != df["fan_status"].shift()
    )
    stretch_id = new_stretch.cumsum()
    rows_in_stretch = df.groupby(stretch_id).cumcount()
    minutes = rows_in_stretch * pd.Timedelta(SAMPLING) / pd.Timedelta("1min")
    return minutes.where(df["fan_status"] == 1)
