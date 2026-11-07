# AHU fault detection and diagnosis

Fault detection and diagnosis for 40 air handling units (AHUs) in three buildings, from 5-minute BMS data. The model finds four types of fault (stuck chilled water valve, stuck outdoor air damper, supply air sensor bias, low coil capacity) and says which one it is.

**Where to start:**

- `../report.pdf`: the answers to the four questions, with a summary of the model.
- `notebooks/`: `01` to `04` explore and clean the data (Question 1), `05_modelling` builds and tests the model (Question 2).
- `docs/00 - Project map.md`: the docs (data, data quality, physics, modelling, architecture, every decision with its reason).

## The approach in short

1. **Clean the data.** Each building had its own problem (an office week stamped 8 hours early, a repeated mall day, a hospital outage, wrong units, CO2 glitches, frozen sensors). `clean_sensors()` fixes all of them, on train and test.
2. **Compare every machine with its own normal.** Machines differ a lot, so every feature is a residual against the same machine's healthy behaviour, built from the physics of each fault.
3. **LightGBM decides *if* there is a fault, physics rules decide *which*.** Then rows become alarms: model at least 80% sure, at least 2 hours long, pieces of one fault joined, one type per alarm.
4. **Score like the brief, by event,** on three time blocks the model never saw during training.

| Validation (29 events, about 240 machine-months) | Result |
|---|---|
| Faults found | 100% |
| Right fault type | 93% |
| Median delay | about 10 hours |
| False alarms | 0.05 per AHU per month (about one per machine every 20 months) |

On the test period (July and August) the model raises 14 alarms in 40 machines.

## Assumptions

- The buildings are in Singapore (UTC+8, and the office closed on the 2025 Singapore public holidays).
- Only rows with the fan on are scored; the model predicts `normal` with the fan off and in the first 30 minutes after a start.
- One fault without a work order (stuck damper on B1-AHU-11, 22 to 30 April) is added as a training label (`EXTRA_LABELS` in `config.py`).
- The 28 work orders of the client are trusted as labels, dates included (notebook 04 checks them against the data).

## Folder structure

```text
code/
├── README.md, requirements.txt, pyproject.toml, pytest.ini
├── src/ahu_fdd/       # the package: config, data cleaning, features, rules, model, scoring, simulation, triage, predict
├── notebooks/         # 01_data_overview, 02_data_quality, 03_patterns, 04_faults, 05_modelling
├── tests/unit/        # unit tests on small synthetic data (no client data needed)
├── figures/           # figures of the notebooks and the report
├── artifacts/         # the trained model and its model card, per version
├── docs/              # Obsidian vault: project map, data, quality, physics, modelling, architecture, decisions
├── report/            # sources of ../report.pdf (Markdown per question) and the LaTeX build
└── app/               # optional fault simulator (Streamlit)
```

## Setup

Python 3.11.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

`pip install -e .` installs the `ahu_fdd` package from `src/`, so tests, notebooks and the app can import it from any folder.

The code reads the assignment data from `../../assignment/data/` by default. To use another folder, set `AHU_DATA_DIR` to the folder with `ahu_train.parquet`, `ahu_test.parquet`, `fault_labels_train.csv` and `ahu_metadata.csv`:

```bash
export AHU_DATA_DIR=/path/to/data
```

## How to run and check everything

All commands from this folder (`code/`), with the environment active. About 12 to 15 minutes in total, half of it notebook 05.

| # | What | Command | Time | What you should see |
|---|---|---|---|---|
| 1 | Unit tests | `pytest -q --cov` | ~5 s | All tests pass, coverage about 91% (minimum 75%) |
| 2 | Lint | `ruff check . && ruff format --check .` | ~2 s | `All checks passed!` |
| 3 | Train and predict (the whole pipeline) | `python -m ahu_fdd.predict` | ~1 min | `Wrote 711,994 rows to ../predictions.csv (14 alarms)` and the model saved in `artifacts/lgbm-v<version>/` |
| 4 | Format of the predictions | `python <assignment>/starter/validate_submission.py ../predictions.csv` | ~5 s | `OK: 711994 rows, format is valid` |
| 5 | Notebooks 01 to 04 (Question 1) | Run all, kernel "Python 3.11" | ~30-40 s each | No errors |
| 6 | Notebook 05 (Question 2) | Run all | ~6-8 min | No errors; final model 100% found, 93% right type, 0.05 false alarms per AHU per month |
| 7 | The report | `python report/build.py` | ~25 s | `9 main pages (OK, max 12) + 4 appendix` |
| 8 | The fault simulator | `streamlit run app/streamlit_app.py` | ~30 s first load | Opens in the browser; "stuck tap" with the defaults: detected after 8 h, right type, no false alarm |

Notes:

- **There is no separate training command:** step 3 validates on the three time blocks, trains the final model on January to June, predicts July and August, and saves the model with its model card. Notebook 05 trains many models too, but only to compare options; it does not save them.
- **Order:** run step 3 before notebook 05, because its last section reads `../predictions.csv`. The notebooks only write figures, so `predict` doesn't depend on them.
- To run all notebooks from the terminal: `cd notebooks && for n in 01_data_overview 02_data_quality 03_patterns 04_faults 05_modelling; do jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=2400 $n.ipynb; done`
- Step 7 needs pandoc and tectonic (`brew install pandoc tectonic`); the first build downloads LaTeX packages (1-2 minutes).
- Step 8 needs Streamlit: `pip install -r app/requirements-app.txt`. Details in [app/README.md](app/README.md).

## Repository

All the work is also on GitHub: https://github.com/serrasm19/ahu-fault-detection

- Full history: one branch per phase, merged through pull requests with CI checks (lint, tests with at least 75% coverage, branch policy, changelog check).
- Latest release: [`v1.0.0`](https://github.com/serrasm19/ahu-fault-detection/releases/tag/v1.0.0), the final submission. **The ZIP of this submission matches this release.**
- Claude skills for alarm triage, sensitivity tests and project checks: `.claude/skills/` in the repository, explained in [`docs/07 - Claude skills.md`](docs/07%20-%20Claude%20skills.md). They came after the delivery, so they are not in the ZIP.
- Changes per version: [`CHANGELOG.md`](https://github.com/serrasm19/ahu-fault-detection/blob/main/CHANGELOG.md).
