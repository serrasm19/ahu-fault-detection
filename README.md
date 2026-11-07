# AHU fault detection

Fault detection and diagnosis for air handling units (AHUs), from 5-minute building management system (BMS) data. The model finds faults such as a stuck chilled-water valve or a biased supply air sensor, and says which type they are.

This is a personal project. The sample data is not in this repository.

**Latest release:** [`v1.0.0`](https://github.com/serrasm19/ahu-fault-detection/releases/tag/v1.0.0), with the report, code, predictions and the fault simulator.

## Structure

```text
.claude/skills/       # Claude skills
project/
├── code/             # Python package, notebooks, tests, docs, trained model (artifacts/), report sources (report/)
├── predictions.csv   # fault type for every row of the test period (python -m ahu_fdd.predict)
└── report.pdf        # answers to the four questions (python report/build.py)
```

How to set up and run the code: [project/code/README.md](project/code/README.md).

## Claude skills

`.claude/skills/` holds five project skills: written procedures with scripts that Claude Code follows.

| Skill | What it does |
|---|---|
| `ahu-alarm-triage` | Explains one alarm from the sensors and says what to check on site |
| `fault-sensitivity-test` | Finds how small a simulated fault the detector can still catch |
| `definition-of-done` | Checks tests, lint and the files that change together before a commit |
| `notebook-consistency` | Compares the numbers in notebooks and report with the real outputs |
| `release-and-package` | Runs a release and tests the ZIP in a clean folder (only starts by hand) |

What each one does, how to use it, the results and the limits: [07 - Claude skills](project/code/docs/07%20-%20Claude%20skills.md).

## Branches and CI

```text
feature/*  ->  develop  ->  qa  ->  main
```

- `develop`, `qa` and `main` are protected. Changes only go in through pull requests.
- New work starts in a `feature/*` branch from `develop`.
- Every pull request runs lint (ruff), the tests with a minimum coverage of 75%, and a check that the branch flow above is respected.
- Every pull request also runs `release-check`: `CHANGELOG.md` must have a valid version heading.

## Releases

Changes are listed in [CHANGELOG.md](CHANGELOG.md), one section per version (`## [X.Y.Z] - YYYY-MM-DD`).

1. Each feature pull request adds its entries under the current version, which keeps the date `YYYY-MM-DD`.
2. To release, a `feature/release-X.Y.Z` branch sets the real date. It then goes through `develop` and `qa` to `main`.
3. Pull requests into `main` are blocked if the date is missing or the version was already released.
4. When it reaches `main`, a workflow creates the tag `vX.Y.Z` and a GitHub Release with the notes from the changelog.

