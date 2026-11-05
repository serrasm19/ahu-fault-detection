"""Turn row predictions into alarms a technician can trust."""

import pandas as pd

from ahu_fdd.config import MAX_GAP_ROWS, MIN_ALARM_ROWS, NORMAL


def drop_short_alarms(
    df: pd.DataFrame, pred: pd.Series, *, min_rows: int = MIN_ALARM_ROWS
) -> pd.Series:
    """Set to normal every alarm shorter than min_rows fan-on rows.

    A real fault lasts days; a few odd rows (a storm, a start) are not worth a site visit.
    Fan-off rows are skipped, so an alarm can continue the next morning.
    Expects df sorted by ahu_id and timestamp, with pred aligned to df.
    """
    on = df["fan_status"] == 1
    label = pred[on]
    ahu = df.loc[on, "ahu_id"]
    # Same logic as rows_to_events: a new run when the AHU or the label changes
    run_id = ((ahu != ahu.shift()) | (label != label.shift())).cumsum()
    run_rows = run_id.groupby(run_id).transform("size")
    out = pred.copy()
    short = run_rows[(run_rows < min_rows) & (label != NORMAL)].index
    out[short] = NORMAL
    return out


def one_type_per_alarm(df: pd.DataFrame, pred: pd.Series) -> pd.Series:
    """Give each alarm a single fault type: the one most of its rows predict.

    An alarm is a run of consecutive fan-on fault rows of one AHU, whatever the type. A
    technician gets one work order with one fault, not a type that changes every 5 minutes.
    Expects df sorted by ahu_id and timestamp, with pred aligned to df.
    """
    on = df["fan_status"] == 1
    is_fault = pred[on] != NORMAL
    ahu = df.loc[on, "ahu_id"]
    alarm_id = ((ahu != ahu.shift()) | (is_fault != is_fault.shift())).cumsum()
    # Most common type inside each alarm (normal runs keep "normal")
    main_type = pred[on].groupby(alarm_id).transform(lambda types: types.mode().iloc[0])
    out = pred.copy()
    out[on] = main_type
    return out


def type_from_rules(df: pd.DataFrame, pred: pd.Series, rule_pred: pd.Series) -> pd.Series:
    """Keep the model's alarms, but take the fault type from the physics rules when they fire.

    The model is better at saying *if* something is wrong (fewer false alarms), the rules at
    saying *what* is wrong. If no rule fires inside an alarm, the model's type stays.
    Expects df sorted by ahu_id and timestamp, with both predictions aligned to df.
    """
    on = df["fan_status"] == 1
    is_fault = pred[on] != NORMAL
    ahu = df.loc[on, "ahu_id"]
    alarm_id = ((ahu != ahu.shift()) | (is_fault != is_fault.shift())).cumsum()
    # Rule types inside the model's alarms only
    rule_types = rule_pred[on].where(is_fault & (rule_pred[on] != NORMAL))

    def main_rule_type(types: pd.Series):
        found = types.dropna()
        return found.mode().iloc[0] if len(found) else None

    from_rules = rule_types.groupby(alarm_id).transform(main_rule_type).dropna()
    out = pred.copy()
    out[from_rules.index] = from_rules
    return out


def bridge_short_gaps(
    df: pd.DataFrame, pred: pd.Series, *, max_rows: int = MAX_GAP_ROWS
) -> pd.Series:
    """Fill short normal gaps between two alarms of the same AHU, so they become one alarm.

    Every morning the first 30 minutes after start-up are forced to normal, which would cut
    a fault that lasts days into one alarm per day. The gap takes the type of the alarm before.
    Expects df sorted by ahu_id and timestamp, with pred aligned to df.
    """
    on = df["fan_status"] == 1
    label = pred[on]
    ahu = df.loc[on, "ahu_id"]
    is_fault = label != NORMAL
    run_id = ((ahu != ahu.shift()) | (is_fault != is_fault.shift())).cumsum()
    run_rows = run_id.groupby(run_id).transform("size")
    # A normal run is a gap to fill if it is short and has an alarm of the same AHU on each side
    previous_type = label.where(is_fault).groupby(ahu).ffill()
    next_type = label.where(is_fault).groupby(ahu).bfill()
    fill = (~is_fault) & (run_rows <= max_rows) & previous_type.notna() & next_type.notna()
    out = pred.copy()
    out[fill[fill].index] = previous_type[fill]
    return out
