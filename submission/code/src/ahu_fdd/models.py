"""Train a classifier on the model features and turn its output into fault predictions."""

import json
from pathlib import Path

import pandas as pd
from lightgbm import LGBMClassifier

from ahu_fdd.config import (
    ALARM_MIN_PROB,
    LGBM_PARAMS,
    NORMAL,
    NORMAL_KEEP_SHARE,
    SEED,
    STARTUP_MINUTES,
)
from ahu_fdd.features import MODEL_FEATURES


def training_rows(
    df: pd.DataFrame, *, normal_share: float = NORMAL_KEEP_SHARE, seed: int = SEED
) -> pd.DataFrame:
    """Rows to learn from: running after start-up, every fault row and a sample of healthy rows.

    Healthy rows repeat a lot (2 million of them), so a sample keeps the same information
    and makes training much faster. Nothing is invented: no fake fault rows.
    """
    running = df[df["minutes_on"] >= STARTUP_MINUTES]
    faults = running[running["label"] != NORMAL]
    healthy = running[running["label"] == NORMAL].sample(frac=normal_share, random_state=seed)
    return pd.concat([faults, healthy]).sort_index()


def build_lgbm() -> LGBMClassifier:
    """The main model, with the settings from config.py."""
    return LGBMClassifier(**LGBM_PARAMS, random_state=SEED)


def fit_model(model, train: pd.DataFrame, features: list[str] = MODEL_FEATURES):
    """Fit any scikit-learn style classifier on the model features."""
    return model.fit(train[features], train["label"])


def fault_proba(model, df: pd.DataFrame, features: list[str] = MODEL_FEATURES) -> pd.DataFrame:
    """Probability of each class (normal and the four faults) for every row."""
    return pd.DataFrame(model.predict_proba(df[features]), columns=model.classes_, index=df.index)


def predict_faults(
    model,
    df: pd.DataFrame,
    *,
    min_prob: float = ALARM_MIN_PROB,
    features: list[str] = MODEL_FEATURES,
) -> pd.Series:
    """Most likely fault per row, or normal if the model is unsure or the AHU is not running."""
    faults = fault_proba(model, df, features).drop(columns=NORMAL)
    best = faults.idxmax(axis=1)
    pred = best.where(faults.max(axis=1) >= min_prob, NORMAL)
    # Same rule as everywhere: no alarms with the fan off or during the start-up
    return pred.where(df["minutes_on"] >= STARTUP_MINUTES, NORMAL)


def save_model(model: LGBMClassifier, card: dict, folder: Path) -> Path:
    """Save a fitted LightGBM model (readable text file) and its model card (JSON)."""
    folder.mkdir(parents=True, exist_ok=True)
    model.booster_.save_model(folder / "model.txt")
    (folder / "model_card.json").write_text(json.dumps(card, indent=2, default=str) + "\n")
    return folder
