"""Features built from the cleaned sensor log."""

import numpy as np
import pandas as pd

from ahu_fdd.config import MIN_MIX_DELTA_C, MIN_REST_MINUTES, MIN_VALVE_PCT, SAMPLING


def _minutes_in_fan_state(df: pd.DataFrame) -> pd.Series:
    """Minutes since the fan last changed state (on to off or off to on), per AHU."""
    # A new "stretch" starts when the AHU changes or the fan status changes
    new_stretch = (df["ahu_id"] != df["ahu_id"].shift()) | (
        df["fan_status"] != df["fan_status"].shift()
    )
    rows_in_stretch = df.groupby(new_stretch.cumsum()).cumcount()
    return rows_in_stretch * pd.Timedelta(SAMPLING) / pd.Timedelta("1min")


def minutes_since_fan_on(df: pd.DataFrame) -> pd.Series:
    """Minutes since the fan last started (0 on the first row with the fan on), NaN with fan off.

    Expects df sorted by ahu_id and timestamp.
    """
    return _minutes_in_fan_state(df).where(df["fan_status"] == 1)


def sat_error(df: pd.DataFrame) -> pd.Series:
    """Supply air temperature minus its setpoint, °C (positive = warmer than asked)."""
    return df["sat_c"] - df["sat_sp_c"]


def outdoor_air_fraction(df: pd.DataFrame, *, min_delta_c: float = MIN_MIX_DELTA_C) -> pd.Series:
    """Share of outdoor air in the mixed air: x = (MAT - RAT) / (OAT - RAT).

    NaN when outdoor and return air are too close, because then the formula divides by
    almost zero. Same formula as outdoor_air_fraction() in the starter ahu_utils.py.
    """
    delta = df["oat_c"] - df["rat_c"]
    return ((df["mat_c"] - df["rat_c"]) / delta).where(delta.abs() >= min_delta_c)


def cooling_per_valve(df: pd.DataFrame, *, min_valve_pct: float = MIN_VALVE_PCT) -> pd.Series:
    """Air cooled by the coil (MAT - SAT, °C) per 100% of valve opening.

    A weak coil cools less for the same opening. NaN when the valve is almost closed.
    """
    valve = df["chw_valve_cmd_pct"]
    per_valve = (df["mat_c"] - df["sat_c"]) / valve * 100
    return per_valve.where(valve >= min_valve_pct)


def sat_offset_at_rest(df: pd.DataFrame, *, min_minutes: float = MIN_REST_MINUTES) -> pd.Series:
    """Supply minus mixed air temperature when the fan has been off for a while, else NaN.

    With the fan off the air in the unit is still, so both sensors should read almost the
    same. A large offset points to a biased supply air sensor.
    Expects df sorted by ahu_id and timestamp.
    """
    at_rest = (df["fan_status"] == 0) & (_minutes_in_fan_state(df) >= min_minutes)
    return (df["sat_c"] - df["mat_c"]).where(at_rest, np.nan)
