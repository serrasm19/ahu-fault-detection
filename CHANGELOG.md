# Changelog

All notable changes to this project are documented in this file.

Each version starts as `## [X.Y.Z] - YYYY-MM-DD`. The date is set in the last pull request before the release to `main`, which then gets the tag `vX.Y.Z`.

## [0.2.0] - YYYY-MM-DD

### Added general
- Documentation vault in `submission/code/docs/` (Obsidian, normal Markdown links): project map, data, data quality, AHU physics and faults, modelling, architecture, development workflow and decisions log.

### Added DevOps
- One `feature/*` branch per phase and releases only at milestones (`v0.2.0` model end to end, `v1.0.0` final submission).

### Added data and EDA
- Data helpers: `add_building()`, `label_rows()` (paints each sensor row with its fault or `normal`), plain fault names in `config.py`.
- EDA helpers in `eda.py`: coverage per machine and per building (duplicates and missing 5-minute slots), fan-on hours per fault event.
- Shared plot style and `save_fig()` for report figures.
- Notebook `01_data_overview`: the four tables, coverage, real schedules, Singapore public holidays, one office week stamped 8 hours early (UTC instead of local time), fault labels and class balance.
- Plain-language docs for the data tables, the AHU and the four faults, and the first data quality findings.

## [0.1.0] - 2026-11-04

### Added general
- Project skeleton: `ahu_fdd` package with config and data loaders, README and decisions log.
- Unit tests on small synthetic data, so they run without the client data.

### Added DevOps
- CI on every pull request: lint and format check with ruff, tests with a minimum coverage of 75%, and a branch policy check (`feature/*` -> `develop` -> `qa` -> `main`).
- Protected `develop`, `qa` and `main` branches: pull requests only, required checks, no force push or deletion.
- Changelog, a `release-check` job that blocks undated or repeated versions on `main`, and a release workflow that tags `vX.Y.Z` and publishes a GitHub Release from this file.
