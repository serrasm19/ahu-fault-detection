# AHU fault detection

Fault detection and diagnosis for air handling units (AHUs), from 5-minute building management system (BMS) data. The model finds faults such as a stuck chilled-water valve or a biased supply air sensor, and says which type they are.

The client data is not in this repository.

## Structure

```text
submission/
├── code/             # Python package, notebooks, tests, docs
├── report.pdf        # added at the end
└── predictions.csv   # added at the end
```

How to set up and run the code: [submission/code/README.md](submission/code/README.md).

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


