import json

import numpy as np
import pandas as pd

from ahu_fdd.features import MODEL_FEATURES
from ahu_fdd.models import build_lgbm, fit_model, predict_faults, save_model, training_rows


def _fake_rows(n_normal=400, n_fault=200, seed=0):
    """Rows where 'sat_error_dev' alone separates a stuck tap from normal."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        rng.normal(0, 0.3, (n_normal + n_fault, len(MODEL_FEATURES))), columns=MODEL_FEATURES
    )
    df.loc[n_normal:, "sat_error_dev"] += 8
    df["label"] = ["normal"] * n_normal + ["chw_valve_stuck"] * n_fault
    df["minutes_on"] = 60.0
    return df


def test_training_rows_keeps_all_faults_and_a_share_of_normal_rows():
    df = _fake_rows()
    df.loc[0, "minutes_on"] = 10.0  # start-up row: never used
    rows = training_rows(df, normal_share=0.5)
    assert (rows["label"] == "chw_valve_stuck").sum() == 200
    assert (rows["label"] == "normal").sum() == 200
    assert (rows["minutes_on"] >= 30).all()


def test_lgbm_learns_a_clear_signal_and_respects_start_up():
    df = _fake_rows()
    model = fit_model(build_lgbm(), df)
    new = _fake_rows(n_normal=5, n_fault=5, seed=1)
    new.loc[9, "minutes_on"] = 10.0  # a fault row during start-up
    pred = predict_faults(model, new, min_prob=0.8)
    assert pred.iloc[:5].eq("normal").all()
    assert pred.iloc[5:9].eq("chw_valve_stuck").all()
    assert pred.iloc[9] == "normal"


def test_save_model_writes_the_model_and_its_card(tmp_path):
    model = fit_model(build_lgbm(), _fake_rows())
    folder = save_model(model, {"version": "0.2.0", "features": MODEL_FEATURES}, tmp_path / "v")
    assert (folder / "model.txt").read_text().startswith("tree")
    assert json.loads((folder / "model_card.json").read_text())["version"] == "0.2.0"
