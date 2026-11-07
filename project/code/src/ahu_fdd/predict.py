"""Build predictions.csv from the raw data with one command: python -m ahu_fdd.predict"""

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import version

import pandas as pd

from ahu_fdd.config import (
    ALARM_MIN_PROB,
    CODE_DIR,
    FAULT_TYPES,
    LGBM_PARAMS,
    MAX_GAP_ROWS,
    MIN_ALARM_ROWS,
    NORMAL,
    NORMAL_KEEP_SHARE,
    PATHS,
    Paths,
)
from ahu_fdd.data import add_extra_labels, clean_sensors, label_rows, load_labels, load_sensors
from ahu_fdd.evaluation import cross_validate, rows_to_events
from ahu_fdd.features import (
    MODEL_FEATURES,
    add_deviations,
    add_features,
    ahu_baselines,
    valve_curve,
)
from ahu_fdd.models import build_lgbm, fit_model, predict_faults, save_model, training_rows
from ahu_fdd.postprocess import (
    bridge_short_gaps,
    drop_short_alarms,
    one_type_per_alarm,
    type_from_rules,
)
from ahu_fdd.rules import rule_predictions


def with_deviations(
    train: pd.DataFrame, target: pd.DataFrame, target_normal: pd.DataFrame | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Each machine's normal from healthy rows only, then compare train and target with it.

    `target_normal` is for machines with no labelled history (a new AHU or building): their
    normal is taken from these rows (for example their first two weeks), all treated as healthy.
    """
    normal_rows = train
    if target_normal is not None:
        normal_rows = pd.concat([train, target_normal.assign(label=NORMAL)])
    baselines, curve = ahu_baselines(normal_rows), valve_curve(normal_rows)
    return add_deviations(train, baselines, curve), add_deviations(target, baselines, curve)


def to_alarms(
    target: pd.DataFrame,
    pred: pd.Series,
    *,
    min_alarm_rows: int = MIN_ALARM_ROWS,
    max_gap_rows: int = MAX_GAP_ROWS,
) -> pd.Series:
    """Row predictions to alarms: drop short ones, join the pieces of one fault, one type each."""
    # Under 2 hours of running: flicker, storms
    pred = drop_short_alarms(target, pred, min_rows=min_alarm_rows)
    # A gap like the morning start-up doesn't split one fault (0 = don't join)
    pred = bridge_short_gaps(target, pred, max_rows=max_gap_rows)
    return one_type_per_alarm(target, pred)


def rules_predict(
    train: pd.DataFrame, target: pd.DataFrame, *, target_normal: pd.DataFrame | None = None
) -> pd.Series:
    """Alarms from the physics rules only. Needs no labelled faults, only each machine's normal."""
    _, target = with_deviations(train, target, target_normal)
    return to_alarms(target, rule_predictions(target))


@dataclass
class FittedPipeline:
    """Everything learned from the training data: each machine's normal and the model."""

    model: object
    baselines: pd.DataFrame
    curve: pd.Series
    features: list[str]

    def deviations(self, target: pd.DataFrame) -> pd.DataFrame:
        """Compare target rows (from add_features) with each machine's normal."""
        return add_deviations(target, self.baselines, self.curve)


def fit_pipeline(
    train: pd.DataFrame,
    *,
    model=None,
    target_normal: pd.DataFrame | None = None,
    features: list[str] = MODEL_FEATURES,
) -> FittedPipeline:
    """Learn each machine's normal from healthy rows and fit the model on labelled `train` rows.

    `target_normal` is for machines with no labelled history (a new AHU or building): their
    normal is taken from these rows (for example their first two weeks), all treated as healthy.
    """
    normal_rows = train
    if target_normal is not None:
        normal_rows = pd.concat([train, target_normal.assign(label=NORMAL)])
    baselines, curve = ahu_baselines(normal_rows), valve_curve(normal_rows)
    train = add_deviations(train, baselines, curve)
    model = build_lgbm() if model is None else model
    model = fit_model(model, training_rows(train), features)
    return FittedPipeline(model, baselines, curve, features)


def predict_alarms(
    fitted: FittedPipeline,
    target: pd.DataFrame,
    *,
    rule_types: bool = True,
    min_prob: float = ALARM_MIN_PROB,
    min_alarm_rows: int = MIN_ALARM_ROWS,
    max_gap_rows: int = MAX_GAP_ROWS,
) -> pd.Series:
    """Alarms for `target` (from add_features) with a fitted pipeline.

    1. Compare each row with its machine's normal.
    2. The model says if there is a fault (sure at 80% or more).
    3. Row predictions become alarms (see to_alarms).
    4. If `rule_types`, each alarm takes its type from the physics rules when they fire.
    The alert settings default to config.py; the simulator app lets you change them.
    """
    target = fitted.deviations(target)
    pred = predict_faults(fitted.model, target, min_prob=min_prob, features=fitted.features)
    pred = to_alarms(target, pred, min_alarm_rows=min_alarm_rows, max_gap_rows=max_gap_rows)
    if rule_types:
        pred = type_from_rules(target, pred, rule_predictions(target))
    return pred


def train_and_predict(
    train: pd.DataFrame,
    target: pd.DataFrame,
    *,
    model=None,
    target_normal: pd.DataFrame | None = None,
    rule_types: bool = True,
    features: list[str] = MODEL_FEATURES,
    min_prob: float = ALARM_MIN_PROB,
    max_gap_rows: int = MAX_GAP_ROWS,
) -> pd.Series:
    """Fit on labelled `train` rows and predict alarms for `target`, in one call.

    Used for validation (each block) and in the notebooks. `features`, `min_prob` and
    `max_gap_rows` are only changed to compare options (notebook 05, "What I tried").
    """
    fitted = fit_pipeline(train, model=model, target_normal=target_normal, features=features)
    return predict_alarms(
        fitted, target, rule_types=rule_types, min_prob=min_prob, max_gap_rows=max_gap_rows
    )


def to_predictions(test_raw: pd.DataFrame, target: pd.DataFrame, pred: pd.Series) -> pd.DataFrame:
    """One row per row of the raw test file: ahu_id, timestamp, fault_type."""
    keyed = target[["ahu_id", "timestamp"]].assign(fault_type=pred.values)
    out = test_raw[["ahu_id", "timestamp"]].merge(keyed, on=["ahu_id", "timestamp"], how="left")
    # Every test row needs a value. The cleaning keeps all test rows, so this is only a safety net
    out["fault_type"] = out["fault_type"].fillna("normal")
    return out


def format_problems(predictions: pd.DataFrame, test_raw: pd.DataFrame) -> list[str]:
    """What is wrong with the predictions file: one row per raw test row, only known labels."""
    problems = []
    if list(predictions.columns) != ["ahu_id", "timestamp", "fault_type"]:
        problems.append(f"wrong columns: {list(predictions.columns)}")
        return problems
    unknown = set(predictions["fault_type"].dropna()) - {NORMAL, *FAULT_TYPES}
    if unknown:
        problems.append(f"unknown fault types: {sorted(unknown)}")
    if predictions["fault_type"].isna().any():
        problems.append("empty fault types")
    if len(predictions) != len(test_raw):
        problems.append(f"{len(predictions)} rows, expected {len(test_raw)}")
    return problems


# Files that change the model: uncommitted edits here mean the commit doesn't tell the full story
CODE_FILES = ("src", "pyproject.toml", "requirements.txt")


def git_commit() -> dict:
    """The code commit that trained the model, and whether the code had uncommitted changes."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=CODE_DIR, capture_output=True, text=True, check=True
        ).stdout.strip()

    try:
        return {
            "commit": git("rev-parse", "--short", "HEAD"),
            "uncommitted": bool(git("status", "--porcelain", *CODE_FILES)),
        }
    except (OSError, subprocess.CalledProcessError):
        return {"commit": "unknown", "uncommitted": None}  # e.g. run from a ZIP, without git


def model_card(train: pd.DataFrame, labels: pd.DataFrame, validation: dict, alarms: int) -> dict:
    """What the model is, what it learned from and how well it did: saved next to the model."""
    return {
        "model": "LightGBM, fault type from the physics rules inside each alarm",
        "version": version("ahu-fdd"),
        "code": git_commit(),
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "train_period": [train["timestamp"].min(), train["timestamp"].max()],
        "fault_events": {"work_orders": int(len(labels)) - 1, "extra_labels": 1},
        "features": MODEL_FEATURES,
        "lgbm_params": LGBM_PARAMS,
        "settings": {
            "alarm_min_prob": ALARM_MIN_PROB,
            "min_alarm_rows": MIN_ALARM_ROWS,
            "max_gap_rows": MAX_GAP_ROWS,
            "normal_keep_share": NORMAL_KEEP_SHARE,
        },
        "validation": {
            "scheme": "3 blocks of about 2 months, each predicted by the other two",
            "events": validation["events"],
            "detected": round(validation["detected"], 3),
            "right_type": round(validation["type_right"], 3),
            "median_delay_h": round(validation["median_delay_h"], 1),
            "false_alarms_per_ahu_month": round(validation["false_alarms_per_ahu_month"], 3),
        },
        "test_alarms": alarms,
    }


def main(paths: Paths = PATHS) -> pd.DataFrame:
    """Validate, train on January to June, predict July and August, save the model and its card."""
    labels = add_extra_labels(load_labels(paths=paths))
    train = clean_sensors(load_sensors("train", paths=paths))
    train["label"] = label_rows(train, labels)
    train = add_features(train)
    test_raw = load_sensors("test", paths=paths)
    test = add_features(clean_sensors(test_raw))

    # Validation score first, so the model card says how good this version is
    validation = cross_validate(train, labels, train_and_predict)

    # Final model on all of January to June
    fitted = fit_pipeline(train)
    pred = predict_alarms(fitted, test)
    predictions = to_predictions(test_raw, test, pred)
    problems = format_problems(predictions, test_raw)
    if problems:
        raise ValueError(f"predictions are not valid: {problems}")
    predictions.to_csv(paths.predictions, index=False)

    alarms = len(rows_to_events(test.assign(pred=pred.values)))
    card = model_card(train, labels, validation, alarms)
    folder = save_model(fitted.model, card, paths.artifacts_dir / f"lgbm-v{card['version']}")
    print(f"Wrote {len(predictions):,} rows to {paths.predictions} ({alarms} alarms)")
    print(f"Saved the model and its card to {folder}")
    return predictions


if __name__ == "__main__":
    main()
