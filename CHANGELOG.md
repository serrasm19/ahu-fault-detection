# Changelog

All notable changes to this project are documented in this file.

Each version starts as `## [X.Y.Z] - YYYY-MM-DD`. The date is set in the last pull request before the release to `main`, which then gets the tag `vX.Y.Z`.

## [1.1.0] - YYYY-MM-DD

### Added general
- The repository now reads as a personal project, with a sample dataset and an example scenario: `submission/` is now `project/`, the default data folder is `data/`, and the report, notebooks, docs and READMEs no longer follow the structure of an exercise.
- The report has new section titles and no page limit in `report/build.py`.

### Added Claude skills
- Five project skills in `.claude/skills/`: `ahu-alarm-triage`, `fault-sensitivity-test`, `definition-of-done`, `notebook-consistency` and `release-and-package` (this one only starts by hand).
- Evaluation cases for `ahu-alarm-triage` in `evals/`: six real cases, with and without the skill.
- New docs note `07 - Claude skills.md`: what each skill does, how to use it, the results and the limits.

### Added modelling
- `format_problems()` checks `predictions.csv` every time `predict` writes it.
- `triage.py`: the evidence for one alarm from the sensors and the rules, and the list of alarms in `predictions.csv`.
- `sensitivity_table()`: one fault at several sizes on one AHU, with a control run with no fault.
- `simulation.py` moved from `app/` to the package, so the app and the skill score a simulation in the same way. `rule_fires()` split out of `rule_predictions()`. `predictions.csv` is unchanged.

### Added DevOps
- `.gitignore` allows `.claude/skills/` and keeps the other local Claude settings out.
- CI lint also covers the skill scripts. New tests check their logic and each `SKILL.md`, and are skipped where the folder is not there.

## [1.0.0] - 2026-11-05

### Added general
- Latest release link and up-to-date structure in the root README.
- Final code README: approach, results, assumptions, folder structure and a step-by-step table to run and check everything (also in the docs and in Appendix G of the report).
- Docs brought up to date with the final code (data flow, commands, model card path).
- Package version 1.0.0; the model is saved as `artifacts/lgbm-v1.0.0/` with its model card (same predictions).

### Added modelling
- Fault injection with simple physics in `simulate.py` (stuck valve, stuck damper, sensor bias, weak coil), with unit tests.
- The pipeline is split into `fit_pipeline()` and `predict_alarms()`, so a trained pipeline can be reused; `predictions.csv` is unchanged.
- Fault simulator app in `app/` (Streamlit, own `requirements-app.txt`): inject a fault into a healthy AHU and see the signal, the model confidence and the alarms, scored by event.

### Added report
- Report sources in `project/code/report/`, one Markdown file per section.
- Architecture section: diagram (`report/architecture_diagram.py`, `figures/architecture.png`) and explanation: edge agent, Delta layers with automatic quality checks, MLflow with champion and challenger, hourly inference, alerting rules, monitoring, onboarding in under a week.
- Architecture note in the docs: flow diagram, mapping from this repository to production, technology choices, edge agent, alerting rules, monitoring and onboarding tables.
- Architecture: environments with Databricks Asset Bundles, a pass/warn/block data quality gate before inference, automatic closing of alarms and a monitoring dashboard.
- Communication section: reply to the facilities manager and internal note to the project lead, with the reasons behind both in Appendix A.
- Report sections for the data analysis (approach, data quality table, patterns, fault physics against the labels) and the model summary, an "At a glance" box and a map of the project on page 1, and an appendix with model details, the test alarms, questions for the client, what I would do with more time (cold start first), the fault simulator with an example, and how to reproduce.
- `report/build.py` builds `project/report.pdf` in LaTeX (pandoc and tectonic) and checks the page count. `pypdf` added to `requirements.txt` for the page check.

## [0.2.0] - 2026-11-05

### Added general
- Documentation vault in `project/code/docs/` (Obsidian, normal Markdown links): project map, data, data quality, AHU physics and faults, modelling, architecture, development workflow and decisions log.

### Added DevOps
- One `feature/*` branch per phase and releases only at milestones (`v0.2.0` model end to end, `v1.0.0` first full version).

### Added data and EDA
- Data helpers: `add_building()`, `label_rows()` (paints each sensor row with its fault or `normal`), plain fault names in `config.py`.
- EDA helpers in `eda.py`: coverage per machine and per building (duplicates and missing 5-minute slots), fan-on hours per fault event.
- Shared plot style and `save_fig()` for report figures.
- Notebook `01_data_overview`: the four tables, coverage, real schedules, Singapore public holidays, one office week stamped 8 hours early (UTC instead of local time), fault labels and class balance.
- Plain-language docs for the data tables, the AHU and the four faults, and the first data quality findings.
- Cleaning step `fix_clock_shift()`: moves the office week stamped 8 hours early (1 to 8 June) to its real time. Notebook `02_data_quality` section 1 proves the shift with the outside temperature of the mall.
- Cleaning step `merge_duplicates()`: keeps one row per machine and stamp and fills empty values from the other copy (mall day 14 February saved twice). Notebook `02_data_quality` section 2.
- EDA helper `gap_blocks()`: joins missing 5-minute slots into blocks. Notebook `02_data_quality` section 3 finds one 8-day outage in the hospital (10 to 18 March) and only 5-10 minute gaps elsewhere.
- Cleaning steps `fix_power_units()` (fan power logged in watts), `blank_co2_limits()` (CO2 glitches) and `blank_frozen()` (frozen temperature sensors), and `clean_sensors()` that runs every fix in order. EDA helper `longest_runs()`. Notebook `02_data_quality` section 4.
- Feature `minutes_since_fan_on()` in the new `features.py`. Notebook `03_patterns`: a normal day, fixed setpoints per machine, start-up, storms, three machines always at their limit, filter drift, train vs test.
- Physics features in `features.py`: `sat_error()`, `outdoor_air_fraction()`, `cooling_per_valve()`, `sat_offset_at_rest()`. EDA helper `event_vs_normal()`. Notebook `04_faults`: the fingerprint of each fault, label dates vs data, and one stuck flap without a label (B1-AHU-11).

### Added modelling
- Event-level scorer in `evaluation.py` (detection, delay, type, false alarms per AHU per month) and three validation blocks of about two months.
- Extra training label for the stuck flap of B1-AHU-11 found in notebook 04 (`EXTRA_LABELS`).
- Model features in `features.py`: smoothed physics signals, per-AHU baselines and `valve_excess` (valve vs what the machine needs for the same cooling work).
- Rules baseline in `rules.py` and a filter for alarms shorter than 2 hours in `postprocess.py`. Validation: 100% of events found, 93% right type, 0.20 false alarms per AHU per month.
- LightGBM model (`models.py`, `lightgbm==4.7.0`) on 9 features compared with each machine's own normal. It decides if there is a fault; the physics rules give the type.
- Alarm post-processing: one type per alarm, rule types inside model alarms, and joining the pieces of one fault split by short gaps.
- `python -m ahu_fdd.predict` validates, trains, builds `predictions.csv` from the raw data and saves the model with its model card in `artifacts/lgbm-v<version>/`. Validation: 100% of events found, 93% right type, 10 h median delay, 0.05 false alarms per AHU per month.
- Notebook `05_modelling`: framing, features, validation, comparison with rules, logistic regression and random forest, the tests behind the final settings (features, threshold, joining alarms), error analysis, new building test, test alarms.

## [0.1.0] - 2026-11-04

### Added general
- Project skeleton: `ahu_fdd` package with config and data loaders, README and decisions log.
- Unit tests on small synthetic data, so they run without the sample data.

### Added DevOps
- CI on every pull request: lint and format check with ruff, tests with a minimum coverage of 75%, and a branch policy check (`feature/*` -> `develop` -> `qa` -> `main`).
- Protected `develop`, `qa` and `main` branches: pull requests only, required checks, no force push or deletion.
- Changelog, a `release-check` job that blocks undated or repeated versions on `main`, and a release workflow that tags `vX.Y.Z` and publishes a GitHub Release from this file.
