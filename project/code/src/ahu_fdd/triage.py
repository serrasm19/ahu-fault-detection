"""Evidence for one alarm: what the sensors show, compared with the same machine's normal.

Used by the ahu-alarm-triage skill. There is no model here, only the cleaning, the features
and the physics rules, so every number can be traced to the sensors.
"""

import pandas as pd

from ahu_fdd.config import (
    FAULT_NAMES,
    FAULT_TYPES,
    FROZEN_SENSORS,
    NORMAL,
    PATHS,
    RULES,
    STARTUP_MINUTES,
    Paths,
)
from ahu_fdd.data import add_extra_labels, clean_sensors, label_rows, load_labels, load_sensors
from ahu_fdd.evaluation import rows_to_events
from ahu_fdd.features import add_deviations, add_features, ahu_baselines, valve_curve
from ahu_fdd.rules import rule_fires, rule_predictions

# The signals of each fault: column in the running rows and the same machine's normal
SIGNALS = {
    "supply_air_error_c": ("sat_error_run", "base_sat_error"),
    "valve_command_pct": ("chw_valve_cmd_pct_run", "base_chw_valve_cmd_pct"),
    "valve_above_usual_for_same_work": ("valve_excess", None),
    "outdoor_air_fraction": ("oa_fraction_run", "base_oa_fraction"),
    "damper_command_pct": ("oa_damper_cmd_pct", "base_oa_damper_cmd_pct"),
    "co2_ppm": ("co2_ppm", "base_co2_ppm"),
    "offset_at_rest_c": ("last_rest_offset", "base_rest_offset"),
}

# What each rule asks, in words, from the settings in config.py
RULE_TEXT = {
    "chw_valve_stuck": (
        f"supply air more than {RULES['tap_error_c']} °C away from normal and valve command "
        f"at 0% or 100% for over {RULES['tap_at_limit']:.0%} of the last hour"
    ),
    "oa_damper_stuck": (
        f"outdoor air fraction at least {RULES['flap_fraction_drop']} below normal and "
        f"under {RULES['flap_fraction_max']}"
    ),
    "sat_sensor_bias": f"offset at rest more than {RULES['bias_offset_c']} °C away from normal",
    "low_coil_capacity": (
        f"valve over {RULES['weak_valve_excess']} points above usual for the same work, "
        "with the supply air still near normal"
    ),
}


def load_ahu(ahu_id: str, *, paths: Paths = PATHS) -> pd.DataFrame:
    """All rows of one AHU, cleaned, with features and compared with its own healthy rows.

    The normal comes only from the labelled months. The test rows have an empty label.
    """
    train = load_sensors("train", paths=paths)
    test = load_sensors("test", paths=paths)
    if ahu_id not in set(train["ahu_id"]):
        raise ValueError(f"unknown AHU {ahu_id!r}")
    train = clean_sensors(train[train["ahu_id"] == ahu_id].reset_index(drop=True))
    test = clean_sensors(test[test["ahu_id"] == ahu_id].reset_index(drop=True))

    labels = add_extra_labels(load_labels(paths=paths))
    train["label"] = label_rows(train, labels)
    healthy = add_features(train)
    baselines, curve = ahu_baselines(healthy), valve_curve(healthy)

    # Features on both periods joined, so the windows don't restart on 1 July
    rows = add_features(pd.concat([train, test], ignore_index=True))
    return add_deviations(rows, baselines, curve)


def _rounded(value: float) -> float | None:
    """A number ready for JSON: two decimals, or None if it is missing."""
    return None if pd.isna(value) else round(float(value), 2)


def alarm_evidence(
    rows: pd.DataFrame, *, start: str | pd.Timestamp, end: str | pd.Timestamp
) -> dict:
    """What the sensors of one AHU show from start to end (from load_ahu). No diagnosis here."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    window = rows[(rows["timestamp"] >= start) & (rows["timestamp"] < end)]
    if window.empty:
        raise ValueError(f"no rows between {start} and {end}")
    running = window[window["minutes_on"] >= STARTUP_MINUTES]

    signals = {}
    for name, (column, base) in SIGNALS.items():
        value = running[column].median()
        normal = 0.0 if base is None else rows[base].iloc[0]
        signals[name] = {
            "window": _rounded(value),
            "normal": _rounded(normal),
            "change": _rounded(value - normal),
        }

    fires = rule_fires(running)
    rules = [
        {
            "fault": fault,
            "plain_name": FAULT_NAMES[fault],
            "rule": RULE_TEXT[fault],
            "share_of_running_rows": _rounded(fires[fault].mean()) or 0.0,
        }
        for fault in FAULT_TYPES
    ]
    rules.sort(key=lambda rule: rule["share_of_running_rows"], reverse=True)

    # The rule type of each row, with its priorities, as the pipeline uses it
    rule_types = rule_predictions(running)
    fault_rows = rule_types[rule_types != NORMAL]

    # Context that changes how far I can trust the rules
    healthy = rows[(rows["label"] == NORMAL) & (rows["minutes_on"] >= STARTUP_MINUTES)]
    at_limit = healthy["chw_valve_cmd_pct_run"].isin([0, 100]).mean()
    return {
        "ahu_id": window["ahu_id"].iloc[0],
        "start": str(start),
        "end": str(end),
        "rows": {
            "window": len(window),
            "running": len(running),
            "fan_on_share": _rounded((window["fan_status"] == 1).mean()),
        },
        "signals": signals,
        "rules": rules,
        "main_rule_type": fault_rows.mode().iloc[0] if len(fault_rows) else NORMAL,
        "context": {
            "valve_at_limit_share_when_healthy": _rounded(at_limit),
            "checks_at_rest_in_window": int(window["rest_offset"].notna().sum()),
            "has_co2_sensor": bool(rows["co2_ppm"].notna().any()),
            "largest_outdoor_drop_1h_c": _rounded(window["oat_change_1h"].min()),
            "outdoor_minus_return_c": _rounded((running["oat_c"] - running["rat_c"]).median()),
            "missing_share_when_running": {
                sensor: _rounded(running[sensor].isna().mean()) for sensor in FROZEN_SENSORS
            },
        },
    }


def list_alarms(*, paths: Paths = PATHS) -> pd.DataFrame:
    """The alarms in predictions.csv: one row per alarm, longest first."""
    pred = pd.read_csv(paths.predictions, parse_dates=["timestamp"])
    fans = load_sensors("test", paths=paths)[["ahu_id", "timestamp", "fan_status"]]
    # Each key can appear twice if the raw test file repeats it: one row is enough for the alarms
    pred = pred.drop_duplicates(["ahu_id", "timestamp"])
    fans = fans.drop_duplicates(["ahu_id", "timestamp"])
    rows = pred.merge(fans, on=["ahu_id", "timestamp"]).sort_values(["ahu_id", "timestamp"])
    alarms = rows_to_events(rows, pred_col="fault_type")
    alarms["plain_name"] = alarms["fault_type"].map(FAULT_NAMES)
    return alarms.sort_values("rows", ascending=False).reset_index(drop=True)
