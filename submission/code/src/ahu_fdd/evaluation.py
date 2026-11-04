"""Event-level scoring, the way the brief describes it, and time-based validation folds."""

import pandas as pd

from ahu_fdd.config import NORMAL

DAYS_PER_MONTH = 30.44


def rows_to_events(df: pd.DataFrame, pred_col: str = "pred") -> pd.DataFrame:
    """Join predicted fault rows into events: consecutive fan-on rows of one AHU with one label.

    Fan-off rows are skipped, so a fault that continues the next morning stays one event.
    Expects df sorted by ahu_id and timestamp.
    """
    on = df[df["fan_status"] == 1]
    label = on[pred_col]
    # A new event starts when the AHU or the predicted label changes from one fan-on row to the next
    new_run = (on["ahu_id"] != on["ahu_id"].shift()) | (label != label.shift())
    runs = on.assign(run=new_run.cumsum())
    runs = runs[runs[pred_col] != NORMAL]
    events = runs.groupby("run").agg(
        ahu_id=("ahu_id", "first"),
        fault_type=(pred_col, "first"),
        start=("timestamp", "min"),
        end=("timestamp", "max"),
        rows=("timestamp", "size"),
    )
    return events.reset_index(drop=True)


def score_events(df: pd.DataFrame, labels: pd.DataFrame, pred_col: str = "pred") -> dict:
    """Score row predictions per event: detection, delay, right type and false alarms.

    - An event is detected if at least one of its fan-on rows is predicted as any fault.
    - Delay: hours from the event start to the first predicted fault row inside it.
    - The type is right if the most common predicted fault inside the event is the true one.
    - A false alarm is a predicted event that doesn't touch any true event of that AHU.
    """
    on = df[df["fan_status"] == 1]
    per_event = []
    for event in labels.itertuples():
        rows = on[
            (on["ahu_id"] == event.ahu_id)
            & (on["timestamp"] >= event.start)
            & (on["timestamp"] < event.end)
        ]
        flagged = rows[rows[pred_col] != NORMAL]
        detected = len(flagged) > 0
        per_event.append(
            {
                "ahu_id": event.ahu_id,
                "fault_type": event.fault_type,
                "detected": detected,
                "delay_h": (flagged["timestamp"].min() - event.start) / pd.Timedelta("1h")
                if detected
                else float("nan"),
                "predicted_type": flagged[pred_col].mode().iloc[0] if detected else NORMAL,
            }
        )
    per_event = pd.DataFrame(per_event)
    per_event["type_right"] = per_event["predicted_type"] == per_event["fault_type"]

    # False alarms: predicted events that don't overlap any true event of the same AHU
    predicted = rows_to_events(df, pred_col)
    false_alarms = 0
    for alarm in predicted.itertuples():
        true = labels[labels["ahu_id"] == alarm.ahu_id]
        touches = (true["start"] <= alarm.end) & (true["end"] > alarm.start)
        false_alarms += int(not touches.any())

    months = (df["timestamp"].max() - df["timestamp"].min()) / pd.Timedelta(days=DAYS_PER_MONTH)
    ahu_months = df["ahu_id"].nunique() * months
    return {
        "events": len(per_event),
        "detected": float(per_event["detected"].mean()) if len(per_event) else float("nan"),
        "type_right": float(per_event["type_right"].mean()) if len(per_event) else float("nan"),
        "median_delay_h": float(per_event["delay_h"].median()),
        "false_alarms": int(false_alarms),
        "false_alarms_per_ahu_month": false_alarms / ahu_months,
        "per_event": per_event,
    }


def month_folds(timestamps: pd.Series, folds: list[tuple[str, str]]) -> list[pd.Series]:
    """One boolean mask per fold: True for the rows inside [start, end) of that fold."""
    return [(timestamps >= pd.Timestamp(s)) & (timestamps < pd.Timestamp(e)) for s, e in folds]
