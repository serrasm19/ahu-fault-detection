"""Rules baseline: one physics rule per fault, from the fingerprints in notebook 04."""

import pandas as pd

from ahu_fdd.config import NORMAL, RULES, STARTUP_MINUTES


def rule_fires(df: pd.DataFrame, rules: dict = RULES) -> pd.DataFrame:
    """One True/False column per fault: does its rule fire on this row, before any priority?

    Expects the output of add_deviations.
    """
    tap = (df["sat_error_dev"].abs() > rules["tap_error_c"]) & (
        df["valve_at_limit_1h"] > rules["tap_at_limit"]
    )
    flap = (df["oa_fraction_dev"] < -rules["flap_fraction_drop"]) & (
        df["oa_fraction_1h"] < rules["flap_fraction_max"]
    )
    bias = df["rest_offset_dev"].abs() > rules["bias_offset_c"]
    weak = (df["valve_excess"] > rules["weak_valve_excess"]) & (
        df["sat_error_dev"].abs() <= rules["tap_error_c"]
    )
    return pd.DataFrame(
        {
            "chw_valve_stuck": tap,
            "oa_damper_stuck": flap,
            "sat_sensor_bias": bias,
            "low_coil_capacity": weak,
        }
    )


def rule_predictions(df: pd.DataFrame, rules: dict = RULES) -> pd.Series:
    """Fault type per row from simple thresholds. Expects the output of add_deviations.

    When several rules fire, the clearest fault wins: stuck tap, then stuck flap,
    then lying thermometer, then weak radiator.
    """
    fires = rule_fires(df, rules)
    pred = pd.Series(NORMAL, index=df.index, dtype=object)
    # Lowest priority first, so a clearer fault overwrites it
    for fault in ("low_coil_capacity", "sat_sensor_bias", "oa_damper_stuck", "chw_valve_stuck"):
        pred[fires[fault]] = fault
    # No alarms with the fan off or during the start-up (notebook 03)
    pred[~(df["minutes_on"] >= STARTUP_MINUTES)] = NORMAL
    return pred
