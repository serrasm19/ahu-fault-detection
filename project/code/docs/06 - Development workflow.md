# Development workflow

Back to the [project map](00%20-%20Project%20map.md).

## Setup

See the [code README](../README.md). Python 3.11, `pip install -r requirements.txt` and `pip install -e .`.

## Tests and lint

```bash
pytest -q --cov    # fails under 75% coverage (set in pyproject.toml)
ruff check --fix .
ruff format .
```

Unit tests use small synthetic data, so they run without the client data, for example in CI.

## How to run and check everything

The step-by-step table (command, time and what you should see for tests, lint, predictions, notebooks, report and simulator) is in the [code README](../README.md#how-to-run-and-check-everything). In short:

```bash
python -m ahu_fdd.predict            # trains and rebuilds ../predictions.csv and the model card (~1 min)
python report/build.py               # rebuilds ../report.pdf in LaTeX (~25 s, needs pandoc and tectonic)
streamlit run app/streamlit_app.py   # the fault simulator (pip install -r app/requirements-app.txt)
```

## Branches

```text
feature/*  ->  develop  ->  qa  ->  main
```

- One `feature/*` branch per phase of work, merged into `develop` with squash.
- `qa` and `main` only change for a release, with merge commits.
- `develop`, `qa` and `main` are protected: pull requests only, required checks, no force push, no deletion, no exceptions.

## CI checks on every pull request

| Check | What it does |
|---|---|
| `branch-policy` | `develop` only takes `feature/*`, `qa` only takes `develop`, `main` only takes `qa` |
| `release-check` | `CHANGELOG.md` has a valid version heading. Into `main`: the date is set and the version is new |
| `lint` | `ruff check` and `ruff format --check`, on the code and on the skill scripts |
| `tests` | pytest with at least 75% coverage |

## Releases

- Changes go into `CHANGELOG.md` under the current undated version (`## [X.Y.Z] - YYYY-MM-DD`).
- Releases only at real milestones: `v0.1.0` setup and CI, `v0.2.0` when the model builds the predictions end to end, `v1.0.0` final submission.
- To release, a `feature/release-X.Y.Z` branch sets the date, then `develop` → `qa` → `main`.
- On `main`, the `release` workflow creates the tag `vX.Y.Z` and a GitHub Release with the changelog notes. It never moves an existing tag.

## Skills for this workflow

Two steps of this workflow have a skill, so they are not done from memory. `definition-of-done` checks a change before a commit, and `release-and-package` runs a release and tests the ZIP in a clean folder. See [Claude skills](07%20-%20Claude%20skills.md).

## Docs

This folder is a small Obsidian vault. Notes use normal relative Markdown links, so they work in Obsidian, on GitHub and in the ZIP. When a change affects data handling, features, the model, the workflow or the architecture, the matching note is updated in the same pull request.
