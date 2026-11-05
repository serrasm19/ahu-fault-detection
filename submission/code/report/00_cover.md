This report answers Questions 1, 3 and 4, with a summary of Question 2. Code, history and releases are also on GitHub: <https://github.com/serrasm19/ahu-fault-detection> (release `v1.0.0`; the ZIP of this submission matches it).

::: {.glance}
**At a glance**

- **Data (Q1).** Each building had its own data problem: one office week stamped 8 hours early, a mall day saved twice, an 8-day hospital outage, fan power in watts, CO2 glitches and two frozen sensors. I found, proved and fixed each one, and they become automatic checks in production. I also found a stuck damper that has no work order.
- **Model (Q2).** A LightGBM model decides *if* a machine has a fault; physics rules decide *which* one. In validation it found all 29 faults, 93% with the right type, about 10 hours after they started, with about one false alarm per machine every 20 months. It raises 14 alarms in July and August.
- **Architecture (Q3).** Azure and Databricks, an edge agent that only sends data out over HTTPS, hourly inference, a new model only replaces the current one if it is better on the same validation, and alerts designed against alarm fatigue.
- **Client (Q4).** Agree with the facilities manager, check the 9 alerts this week, send only high-confidence alerts, and connect the two new buildings next month without alerts until the pilot shows that 7 of 10 checked alerts are real.
:::

**What is in this submission**

| Where | What |
|-----------------------------|-----------------------------------------------------------------|
| `report.pdf` | This report |
| `predictions.csv` | Fault type for every row of the test period (format checked with `validate_submission.py`) |
| `code/README.md` | Start here: setup, how to rebuild `predictions.csv` and this report |
| `code/notebooks/` | `01`-`04`: data exploration and quality (Q1); `05_modelling`: the model (Q2) |
| `code/src/ahu_fdd/` | Python package used by the notebooks: cleaning, features, rules, model, scoring, `predict.py` |
| `code/tests/`, `code/docs/` | 54 unit tests; docs, including the architecture details (Q3) and every decision with its reason |
| `code/artifacts/`, `code/report/` | Trained model and its model card; the sources of this report |

