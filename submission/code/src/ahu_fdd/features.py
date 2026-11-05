"""Features built from the cleaned sensor log."""

import numpy as np
import pandas as pd

from ahu_fdd.config import (
    LOAD_BIN,
    LONG_WINDOW_ROWS,
    MIN_MIX_DELTA_C,
    MIN_REST_MINUTES,
    MIN_VALVE_PCT,
    NORMAL,
    REST_CHECK_KEEP_ROWS,
    SAMPLING,
    SHORT_WINDOW_ROWS,
    STARTUP_MINUTES,
)


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


# Signals that only mean something while the machine runs, and the AHU baselines I compare with
RUNNING_SIGNALS = ["sat_error", "oa_fraction", "cooling_per_valve", "chw_valve_cmd_pct"]
BASELINE_SIGNALS = [
    "sat_error",
    "oa_fraction",
    "cooling_per_valve",
    "chw_valve_cmd_pct",
    "oa_damper_cmd_pct",
    "co2_ppm",
]

# Columns the model uses. Only signals compared with each machine's own normal (plus the share
# of outdoor air): with raw values the model mixed up faults in the three machines that are
# always at their limit (notebook 03). Tested in notebooks/05_modelling.ipynb
MODEL_FEATURES = [
    "sat_error_dev",
    "valve_dev",
    "valve_at_limit_1h",
    "valve_excess",
    "oa_fraction_1h",
    "oa_fraction_dev",
    "damper_dev",
    "co2_dev",
    "rest_offset_dev",
]


# Raw and context signals I also tried as model features (notebook 05, "What I tried").
# Not used by the final model: see the comment on MODEL_FEATURES
OTHER_FEATURES = [
    "minutes_on",
    "oat_c",
    "oat_change_1h",
    "fan_speed_pct",
    "chw_valve_cmd_pct",
    "oa_damper_cmd_pct",
    "sat_error_1h",
    "sat_error_3h",
    "valve_1h",
    "cooling_per_valve_3h",
]


def _rolling_median(df: pd.DataFrame, col: str, rows: int) -> pd.Series:
    """Median of the last `rows` rows of one AHU (NaN rows are skipped)."""
    rolled = df.groupby("ahu_id")[col].rolling(rows, min_periods=rows // 3).median()
    return rolled.reset_index(level=0, drop=True)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add the physics signals and their 1-hour and 3-hour medians. No labels needed.

    Expects df sorted by ahu_id and timestamp (as clean_sensors returns it).
    """
    out = df.copy()
    out["minutes_on"] = minutes_since_fan_on(out)
    out["sat_error"] = sat_error(out)
    out["oa_fraction"] = outdoor_air_fraction(out)
    out["cooling_per_valve"] = cooling_per_valve(out)
    out["rest_offset"] = sat_offset_at_rest(out)

    # While starting up or off, these signals mean nothing: blank them before smoothing
    running = out["minutes_on"] >= STARTUP_MINUTES
    for col in RUNNING_SIGNALS:
        out[f"{col}_run"] = out[col].where(running)

    # Smooth over 1 and 3 hours, so a single odd reading or a short storm doesn't count
    out["sat_error_1h"] = _rolling_median(out, "sat_error_run", SHORT_WINDOW_ROWS)
    out["sat_error_3h"] = _rolling_median(out, "sat_error_run", LONG_WINDOW_ROWS)
    out["valve_1h"] = _rolling_median(out, "chw_valve_cmd_pct_run", SHORT_WINDOW_ROWS)
    out["oa_fraction_1h"] = _rolling_median(out, "oa_fraction_run", SHORT_WINDOW_ROWS)
    out["cooling_per_valve_3h"] = _rolling_median(out, "cooling_per_valve_run", LONG_WINDOW_ROWS)

    # Share of the last hour with the valve command at a limit (0% or 100%): a stuck tap sign
    at_limit = out["chw_valve_cmd_pct_run"].isin([0, 100]).astype(float)
    at_limit = at_limit.where(running)
    out["valve_at_limit_1h"] = (
        at_limit.groupby(out["ahu_id"]).rolling(SHORT_WINDOW_ROWS, min_periods=4).mean()
    ).reset_index(level=0, drop=True)

    # Weather change over the last hour: a storm can move the valve for a short time
    out["oat_change_1h"] = out["oat_c"] - out.groupby("ahu_id")["oat_c"].shift(SHORT_WINDOW_ROWS)

    # Cooling work: how much air (fan speed share) times how much it is cooled (MAT - SAT).
    # Grouped in steps, to compare the valve with the same machine doing the same work
    work = out["fan_speed_pct"] / 100 * (out["mat_c"] - out["sat_c"])
    out["load_bin"] = (work / LOAD_BIN).round().clip(lower=0).where(running)

    # Last check at rest (fan off for an hour), carried to the next fan-on rows for 48 hours
    out["last_rest_offset"] = out.groupby("ahu_id")["rest_offset"].ffill(limit=REST_CHECK_KEEP_ROWS)
    return out


def ahu_baselines(df: pd.DataFrame) -> pd.DataFrame:
    """Each AHU's normal: medians of the healthy rows (label normal, running after start-up).

    Expects the output of add_features with a 'label' column.
    """
    healthy = df[df["label"] == NORMAL]
    running = healthy[healthy["minutes_on"] >= STARTUP_MINUTES]
    base = running.groupby("ahu_id")[BASELINE_SIGNALS].median()
    base["rest_offset"] = healthy.groupby("ahu_id")["rest_offset"].median()
    return base.add_prefix("base_")


def valve_curve(df: pd.DataFrame) -> pd.Series:
    """Each AHU's usual valve opening for each step of cooling work (healthy running rows).

    A weak coil needs more valve than usual for the same work. Comparing with the same
    machine doing the same work avoids false alarms on hot afternoons (notebook 03).
    """
    healthy = df[(df["label"] == NORMAL) & (df["minutes_on"] >= STARTUP_MINUTES)]
    curve = healthy.groupby(["ahu_id", "load_bin"])["chw_valve_cmd_pct"].median()
    return curve.rename("expected_valve")


def add_deviations(df: pd.DataFrame, baselines: pd.DataFrame, curve: pd.Series) -> pd.DataFrame:
    """Compare each smoothed signal with the same AHU's normal (notebook 03: machines differ)."""
    out = df.join(baselines, on="ahu_id").join(curve, on=["ahu_id", "load_bin"])
    out["sat_error_dev"] = out["sat_error_1h"] - out["base_sat_error"]
    out["valve_dev"] = out["valve_1h"] - out["base_chw_valve_cmd_pct"]
    out["oa_fraction_dev"] = out["oa_fraction_1h"] - out["base_oa_fraction"]
    out["damper_dev"] = out["oa_damper_cmd_pct"] - out["base_oa_damper_cmd_pct"]
    out["co2_dev"] = out["co2_ppm"] - out["base_co2_ppm"]
    # Valve above what this machine usually needs for the same work (0 = as usual), over 3 hours
    out["valve_excess_row"] = out["chw_valve_cmd_pct_run"] - out["expected_valve"]
    out["valve_excess"] = _rolling_median(out, "valve_excess_row", LONG_WINDOW_ROWS)
    out["rest_offset_dev"] = out["last_rest_offset"] - out["base_rest_offset"]
    return out
