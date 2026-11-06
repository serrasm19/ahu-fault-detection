"""Inject a fault into one AHU and run the whole pipeline, once or for several fault sizes.

Used by the fault simulator app (app/), the example figure of the report and the
fault-sensitivity-test skill, so all of them score a simulation in the same way.
"""

from dataclasses import dataclass

import pandas as pd

from ahu_fdd.config import (
    ALARM_MIN_PROB,
    MAX_GAP_ROWS,
    MIN_ALARM_ROWS,
    NORMAL,
    SENSITIVITY_FAULT_DAYS,
    SENSITIVITY_LEAD_DAYS,
    SENSITIVITY_SIZES,
    STARTUP_MINUTES,
)
from ahu_fdd.data import add_extra_labels, clean_sensors, label_rows, load_labels, load_sensors
from ahu_fdd.evaluation import rows_to_events
from ahu_fdd.features import add_features
from ahu_fdd.models import fault_proba
from ahu_fdd.predict import FittedPipeline, fit_pipeline, predict_alarms
from ahu_fdd.simulate import inject_fault

WINDOW_DAYS = 14  # days shown or scored
HISTORY_DAYS = 2  # extra days before the window, so the rolling features are complete


@dataclass
class SimulationResult:
    """What the app shows for one simulation (only the rows of the window shown)."""

    before: pd.DataFrame  # features of the healthy data
    after: pd.DataFrame  # features with the fault injected
    fault_probability: pd.Series  # 1 - P(normal), 0 when not running
    events: pd.DataFrame  # alarms: ahu_id, fault_type, start, end, rows
    detected: bool
    delay_h: float | None
    main_type: str | None
    false_alarms: int


def load_pipeline() -> tuple[FittedPipeline, pd.DataFrame, pd.DataFrame]:
    """Cleaned data of both periods, the labels, and the pipeline trained on January to June."""
    labels = add_extra_labels(load_labels())
    train = clean_sensors(load_sensors("train"))
    train["label"] = label_rows(train, labels)
    fitted = fit_pipeline(add_features(train))
    test = clean_sensors(load_sensors("test"))
    data = pd.concat([train.drop(columns="label"), test], ignore_index=True)
    return fitted, data, labels


def simulate(
    fitted: FittedPipeline,
    data: pd.DataFrame,
    *,
    ahu_id: str,
    window_start: pd.Timestamp,
    fault: str,
    fault_start: pd.Timestamp,
    fault_end: pd.Timestamp,
    size: float,
    min_prob: float,
    min_alarm_rows: int,
    max_gap_rows: int,
) -> SimulationResult:
    """Inject the fault into this AHU's data, run the pipeline and score the result."""
    window_end = window_start + pd.Timedelta(days=WINDOW_DAYS)
    rows = data[
        (data["ahu_id"] == ahu_id)
        & (data["timestamp"] >= window_start - pd.Timedelta(days=HISTORY_DAYS))
        & (data["timestamp"] < window_end)
    ].reset_index(drop=True)
    faulty = inject_fault(
        rows, ahu_id=ahu_id, fault=fault, start=fault_start, end=fault_end, size=size
    )
    before, after = add_features(rows), add_features(faulty)
    alarms = predict_alarms(
        fitted,
        after,
        min_prob=min_prob,
        min_alarm_rows=min_alarm_rows,
        max_gap_rows=max_gap_rows,
    )
    proba = fault_proba(fitted.model, fitted.deviations(after), fitted.features)
    fault_probability = (1 - proba[NORMAL]).where(after["minutes_on"] >= STARTUP_MINUTES, 0.0)

    # Keep only the window shown (the history days were only for the rolling features)
    shown = after["timestamp"] >= window_start
    events = rows_to_events(after.assign(pred=alarms.values)[shown])

    # Score it like the brief: found, delay, right type, false alarms
    in_fault = (events["end"] >= fault_start) & (events["start"] < fault_end)
    caught = events[in_fault] if fault != NORMAL else events.iloc[:0]
    detected = len(caught) > 0
    delay = (max(caught["start"].min(), fault_start) - fault_start) / pd.Timedelta("1h")
    return SimulationResult(
        before=before[shown],
        after=after[shown],
        fault_probability=fault_probability[shown],
        events=events,
        detected=detected,
        delay_h=delay if detected else None,
        main_type=caught["fault_type"].mode().iloc[0] if detected else None,
        false_alarms=len(events) - len(caught),
    )


def sensitivity_table(
    fitted: FittedPipeline,
    data: pd.DataFrame,
    *,
    ahu_id: str,
    fault: str,
    window_start: pd.Timestamp,
    sizes: tuple[float, ...] | None = None,
) -> pd.DataFrame:
    """One row per fault size on one AHU: found, delay, right type, false alarms.

    The first row is a control with no fault. If it has an alarm, the window was not healthy
    and the other rows can't be trusted.
    """
    fault_start = window_start + pd.Timedelta(days=SENSITIVITY_LEAD_DAYS)
    fault_end = fault_start + pd.Timedelta(days=SENSITIVITY_FAULT_DAYS)
    sizes = SENSITIVITY_SIZES[fault] if sizes is None else sizes

    rows = []
    for name, size in [(NORMAL, float("nan")), *((fault, size) for size in sizes)]:
        result = simulate(
            fitted,
            data,
            ahu_id=ahu_id,
            window_start=window_start,
            fault=name,
            fault_start=fault_start,
            fault_end=fault_end,
            size=size,
            min_prob=ALARM_MIN_PROB,
            min_alarm_rows=MIN_ALARM_ROWS,
            max_gap_rows=MAX_GAP_ROWS,
        )
        rows.append(
            {
                "ahu_id": ahu_id,
                "fault": name,
                "size": size,
                "detected": result.detected,
                "delay_h": result.delay_h,
                "predicted_type": result.main_type,
                "right_type": result.main_type == fault,
                "false_alarms": result.false_alarms,
            }
        )
    return pd.DataFrame(rows)
