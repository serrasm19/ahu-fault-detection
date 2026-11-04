# Changelog

All notable changes to this project are documented in this file.

Each version starts as `## [X.Y.Z] - YYYY-MM-DD`. The date is set in the last pull request before the release to `main`, which then gets the tag `vX.Y.Z`.

## [0.1.0] - 2026-11-04

### Added general
- Project skeleton: `ahu_fdd` package with config and data loaders, README and decisions log.
- Unit tests on small synthetic data, so they run without the client data.

### Added DevOps
- CI on every pull request: lint and format check with ruff, tests with a minimum coverage of 75%, and a branch policy check (`feature/*` -> `develop` -> `qa` -> `main`).
- Protected `develop`, `qa` and `main` branches: pull requests only, required checks, no force push or deletion.
- Changelog, a `release-check` job that blocks undated or repeated versions on `main`, and a release workflow that tags `vX.Y.Z` and publishes a GitHub Release from this file.
