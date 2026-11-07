# Project map

Fault detection and diagnosis for air handling units (AHUs), from 5-minute BMS data of 40 units in three buildings. This is the entry point to the docs. You can open this folder as an Obsidian vault, or read it on GitHub.

## Notes

| Note | What it covers | Status |
|---|---|---|
| [Data](01%20-%20Data.md) | The four tables, their columns and the sensors in each building | Done |
| [Data quality](02%20-%20Data%20quality.md) | Problems found in the data and how I handle them | Done |
| [AHU physics and faults](03%20-%20AHU%20physics%20and%20faults.md) | How an AHU works, what a healthy machine does and what each fault looks like | Done |
| [Modelling](04%20-%20Modelling.md) | Approach, features, validation, results and the model card | Done |
| [Architecture](05%20-%20Architecture.md) | How this would run in production: flow, technology choices, alerting, monitoring, onboarding | Done |
| [Development workflow](06%20-%20Development%20workflow.md) | Setup, tests, CI, branches and releases | Done |
| [Claude skills](07%20-%20Claude%20skills.md) | The five skills of this project: what each one does, how to use it, results and limits | Done |
| [Decisions](decisions.md) | Log of the decisions and assumptions I made (42 entries) | Done |

## Notebooks

Read them in order. Each one starts with its goal and ends with a summary.

| Notebook | Question it answers | Brief |
|---|---|---|
| `01_data_overview` | What is in each file, how much data each machine has, when they run, what the labels look like | Q1 |
| `02_data_quality` | Can I trust the data? The problems found, how I proved them and how I clean them | Q1 |
| `03_patterns` | What does a healthy machine look like (daily cycle, start-up, storms, machines at their limit, drift)? | Q1 |
| `04_faults` | How does each fault show in the data, do the labels agree, and is any fault missing a label? | Q1 |
| `05_modelling` | The model: framing, features, validation, results, error analysis, new machines, test predictions | Q2 |

To rebuild `predictions.csv` without the notebooks: `python -m ahu_fdd.predict`.

## Where things are

- Code: `src/ahu_fdd/`
- Notebooks: `notebooks/` (table above)
- Report figures: `figures/`
- Trained model and its model card: `artifacts/`
- Report sources (one Markdown file per question) and the LaTeX build: `report/`, writes `../report.pdf`
- Fault simulator (Streamlit app, optional): `app/`, with its own README
- Claude skills: `.claude/skills/` at the root of the repository (not in the ZIP)
- Tests: `tests/unit/`
- Changes per version: `CHANGELOG.md` at the root of the repository
