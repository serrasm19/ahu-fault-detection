import pandas as pd

from ahu_fdd.predict import git_commit, model_card, to_submission


def test_to_submission_has_one_row_per_raw_test_row():
    raw = pd.DataFrame(
        {
            "ahu_id": ["B1-AHU-01", "B1-AHU-01", "B1-AHU-02"],
            "timestamp": pd.to_datetime(
                ["2025-07-01 00:00", "2025-07-01 00:05", "2025-07-01 00:00"]
            ),
            "sat_c": [13.0, 13.1, 14.0],
        }
    )
    target = raw.iloc[[0, 2]]  # one row missing after cleaning: it must still get a prediction
    pred = pd.Series(["oa_damper_stuck", "normal"], index=target.index)
    out = to_submission(raw, target, pred)
    assert list(out.columns) == ["ahu_id", "timestamp", "fault_type"]
    assert out["fault_type"].tolist() == ["oa_damper_stuck", "normal", "normal"]


def test_git_commit_gives_a_commit_or_unknown():
    info = git_commit()
    assert set(info) == {"commit", "uncommitted"}
    assert isinstance(info["commit"], str)


def test_model_card_has_the_version_data_and_scores():
    train = pd.DataFrame({"timestamp": pd.to_datetime(["2025-01-01 00:00", "2025-06-30 23:55"])})
    labels = pd.DataFrame({"ahu_id": ["B1-AHU-01", "B1-AHU-11"]})
    validation = {
        "events": 29,
        "detected": 1.0,
        "type_right": 0.931,
        "median_delay_h": 9.83,
        "false_alarms_per_ahu_month": 0.0459,
    }
    card = model_card(train, labels, validation, alarms=14)
    assert card["fault_events"] == {"work_orders": 1, "extra_labels": 1}
    assert card["validation"]["right_type"] == 0.931
    assert card["test_alarms"] == 14
    assert card["train_period"][0] == pd.Timestamp("2025-01-01 00:00")
