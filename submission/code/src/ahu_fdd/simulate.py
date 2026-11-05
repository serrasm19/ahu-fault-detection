"""Inject a simulated fault into the healthy data of one AHU, with simple physics.

Each fault changes the sensor columns the way notebook 04 showed in the labelled events.
Used by the interactive simulator (app/) and useful for new buildings with no labels.
"""

import numpy as np
import pandas as pd

from ahu_fdd.config import NORMAL

# For each fault: what "size" means, its range and a default (used by the app sliders)
FAULT_SIZES = {
    "chw_valve_stuck": {"label": "Real valve position (%)", "min": 0, "max": 100, "default": 10},
    "oa_damper_stuck": {"label": "Outdoor air left (%)", "min": 0, "max": 100, "default": 0},
    "sat_sensor_bias": {"label": "Sensor bias (°C)", "min": -4, "max": 4, "default": 2.5},
    "low_coil_capacity": {"label": "Coil capacity left (%)", "min": 20, "max": 100, "default": 50},
}

CO2_RISE_PPM = 700  # extra CO2 with no outdoor air at all (notebook 04: +440 to +1,030 ppm)
CO2_RISE_HOURS = 2  # time to get most of the way there
DAMPER_COMPENSATION = 40  # the controller opens the damper command by about 40 points


def _set(df: pd.DataFrame, rows: pd.Series, col: str, values) -> None:
    """Write values into some rows of a column, keeping the column type (the data is float32)."""
    df.loc[rows, col] = pd.Series(values, index=df.index)[rows].astype(df[col].dtype)


def _stuck_valve(df: pd.DataFrame, rows: pd.Series, position: float) -> None:
    """The valve is stuck at `position` %: the coil cools as if it were there."""
    cooling = df["mat_c"] - df["sat_c"]
    wanted = df["chw_valve_cmd_pct"].clip(lower=5)
    # Cooling scales with the real opening; supply air can't go below the chilled water
    new_sat = (df["mat_c"] - cooling * position / wanted).clip(lower=df["chwst_c"] + 1)
    _set(df, rows, "sat_c", new_sat)
    # The controller tries to fix the error and pushes the command to a limit
    error = df["sat_c"] - df["sat_sp_c"]
    _set(df, rows & (error > 0.5), "chw_valve_cmd_pct", 100.0)
    _set(df, rows & (error < -0.5), "chw_valve_cmd_pct", 0.0)


def _stuck_damper(df: pd.DataFrame, rows: pd.Series, outdoor_left: float, start) -> None:
    """Less (or no) outdoor air: mixed air moves to return air, CO2 rises, the command goes up."""
    share = outdoor_left / 100
    _set(df, rows, "mat_c", df["rat_c"] + (df["mat_c"] - df["rat_c"]) * share)
    _set(
        df,
        rows,
        "oa_damper_cmd_pct",
        (df["oa_damper_cmd_pct"] + DAMPER_COMPENSATION).clip(upper=100),
    )
    # CO2 builds up over a couple of hours (only where there is a CO2 sensor)
    hours = (df["timestamp"] - pd.Timestamp(start)) / pd.Timedelta("1h")
    rise = CO2_RISE_PPM * (1 - share) * (1 - np.exp(-hours / CO2_RISE_HOURS))
    _set(df, rows, "co2_ppm", df["co2_ppm"] + rise)


def _sensor_bias(df: pd.DataFrame, rows: pd.Series, off_rows: pd.Series, bias: float) -> None:
    """The supply sensor reads `bias` °C too high (or low).

    Fan on: the controller trusts the sensor, so the reading stays on target and the valve
    works a little harder (or less). Fan off: nothing corrects it, so the reading moves.
    """
    cooling = (df["mat_c"] - df["sat_c"]).clip(lower=1)
    new_valve = (df["chw_valve_cmd_pct"] * (cooling + bias) / cooling).clip(0, 100)
    _set(df, rows, "chw_valve_cmd_pct", new_valve)
    _set(df, off_rows, "sat_c", df["sat_c"] + bias)


def _weak_coil(df: pd.DataFrame, rows: pd.Series, capacity: float) -> None:
    """The coil gives `capacity` % of its cooling: the valve opens more, then the air warms."""
    needed = df["chw_valve_cmd_pct"] * 100 / capacity
    _set(df, rows, "chw_valve_cmd_pct", needed.clip(upper=100))
    # When the valve can't open enough, only part of the cooling is delivered
    short = rows & (needed > 100)
    cooling = df["mat_c"] - df["sat_c"]
    _set(df, short, "sat_c", df["mat_c"] - cooling * 100 / needed)


def inject_fault(
    df: pd.DataFrame,
    *,
    ahu_id: str,
    fault: str,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    size: float,
) -> pd.DataFrame:
    """Copy of df with a simulated `fault` on `ahu_id` from start to end (end not included).

    `size` means what FAULT_SIZES says for each fault. With fault "normal", df is unchanged.
    Expects the cleaned sensor columns (clean_sensors).
    """
    out = df.copy()
    if fault == NORMAL:
        return out
    in_window = (
        (out["ahu_id"] == ahu_id)
        & (out["timestamp"] >= pd.Timestamp(start))
        & (out["timestamp"] < pd.Timestamp(end))
    )
    running = in_window & (out["fan_status"] == 1)
    if fault == "chw_valve_stuck":
        _stuck_valve(out, running, size)
    elif fault == "oa_damper_stuck":
        _stuck_damper(out, running, size, start)
    elif fault == "sat_sensor_bias":
        _sensor_bias(out, running, in_window & (out["fan_status"] == 0), size)
    elif fault == "low_coil_capacity":
        _weak_coil(out, running, size)
    else:
        raise ValueError(f"unknown fault {fault!r}")
    return out
