"""Rules baseline: one physics rule per fault, from the fingerprints in notebook 04."""

import pandas as pd

from ahu_fdd.config import NORMAL, RULES, STARTUP_MINUTES


def rule_predictions(df: pd.DataFrame, rules: dict = RULES) -> pd.Series:
    """Fault type per row from simple thresholds. Expects the output of add_deviations.

    When several rules fire, the clearest fault wins: stuck tap, then stuck flap,
    then lying thermometer, then weak radiator.
    """
    tap = (df["sat_error_dev"].abs() > rules["tap_error_c"]) & (
        df["valve_at_limit_1h"] > rules["tap_at_limit"]
    )
    flap = (df["oa_fraction_dev"] < -rules["flap_fraction_drop"]) & (
        df["oa_fraction_1h"] < rules["flap_fraction_max"]
    )
    bias = df["rest_offset_dev"].abs() > rules["bias_offset_c"]
    weak = (
        (df["cooling_ratio"] < rules["weak_cooling_ratio"])
        & (df["valve_dev"] > rules["weak_valve_up"])
        & (df["sat_error_dev"].abs() <= rules["tap_error_c"])
    )

    pred = pd.Series(NORMAL, index=df.index, dtype=object)
    # Lowest priority first, so a clearer fault overwrites it
    for fault, fires in [
        ("low_coil_capacity", weak),
        ("sat_sensor_bias", bias),
        ("oa_damper_stuck", flap),
        ("chw_valve_stuck", tap),
    ]:
        pred[fires] = fault
    # No alarms with the fan off or during the start-up (notebook 03)
    pred[~(df["minutes_on"] >= STARTUP_MINUTES)] = NORMAL
    return pred
