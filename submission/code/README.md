# AHU fault detection and diagnosis

Work in progress. The docs start at [docs/00 - Project map.md](docs/00%20-%20Project%20map.md).

## Repository

All the work is also on GitHub: https://github.com/serrasm19/ahu-fault-detection

- Full history: one branch per phase, merged through pull requests with CI checks (lint, tests with at least 75% coverage, branch policy, changelog check).
- Latest release: [`v0.2.0`](https://github.com/serrasm19/ahu-fault-detection/releases/tag/v0.2.0) (EDA, data cleaning and the fault detection model, with `predictions.csv`).
- Changes per version: [`CHANGELOG.md`](https://github.com/serrasm19/ahu-fault-detection/blob/develop/CHANGELOG.md).

## Setup

Python 3.11.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

`pip install -e .` installs the `ahu_fdd` package from `src/`, so tests and notebooks can import it from any folder.

The code reads the data from `../../assignment/data/` by default. To use another folder, set `AHU_DATA_DIR`:

```bash
export AHU_DATA_DIR=/path/to/data
```

## Build predictions.csv

```bash
python -m ahu_fdd.predict
```

It cleans the raw data, scores the model on three validation blocks, trains it on January to June, writes `../predictions.csv` (one row per row of `ahu_test.parquet`) and saves the model with its model card in `artifacts/lgbm-v<version>/`. It takes about one minute. To check the format:

```bash
python ../../assignment/starter/validate_submission.py ../predictions.csv
```

## Fault simulator (optional)

A small Streamlit app to inject a fault into a healthy AHU and see if and when the model raises an alarm. Details in [app/README.md](app/README.md).

```bash
pip install -r app/requirements-app.txt
streamlit run app/streamlit_app.py
```

## Build the report

The report sources are in `report/` (one Markdown file per question). They are turned into `../report.pdf` with LaTeX:

```bash
brew install pandoc tectonic   # once
python report/build.py         # writes ../report.pdf and checks the 12-page limit
```

## Tests and lint

```bash
pytest -q --cov          # fails if coverage is below 75% (set in pyproject.toml)
ruff check --fix .
ruff format .
```

Unit tests use small synthetic data, so they also run without the client data (for example in CI).
