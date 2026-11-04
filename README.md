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
