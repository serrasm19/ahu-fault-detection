# AHU fault detection and diagnosis

Work in progress.

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

## Tests and lint

```bash
pytest -q --cov          # fails if coverage is below 75% (set in pyproject.toml)
ruff check --fix .
ruff format .
```

Unit tests use small synthetic data, so they also run without the client data (for example in CI).
