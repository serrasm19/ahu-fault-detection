"""Turn row predictions into alarms a technician can trust."""

import pandas as pd

from ahu_fdd.config import MIN_ALARM_ROWS, NORMAL


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
