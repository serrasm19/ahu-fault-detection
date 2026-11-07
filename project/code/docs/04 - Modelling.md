# Modelling

Back to the [project map](00%20-%20Project%20map.md).

The work is in `notebooks/05_modelling.ipynb` and `src/ahu_fdd/`. `python -m ahu_fdd.predict` rebuilds `predictions.csv` from the raw data.

## How I score a model

In plain words: before the real exam (July and August, with no labels), I do practice exams on January to June, where I know the answers, and I mark them the way a maintenance team would. Without this, every model choice would be a guess.

What matters is the fault event, not the row (a model that always says "normal" is right on 97.6% of the rows and useless). `src/ahu_fdd/evaluation.py` does this, on fan-on rows only:

| Question | How I measure it |
|---|---|
| Is the fault found? | At least one row of the event is predicted as a fault |
| How quickly? | Hours from the event start to the first predicted fault row |
| Is the type right? | The most common predicted fault inside the event is the true one |
| How many false alarms? | Predicted events (consecutive fan-on rows with the same fault) that touch no true event, per AHU per month |

A predicted fault that continues the next morning after the fan was off at night stays one alarm, like one work order.

## Validation

Three blocks of about two months: 1 Jan to 2 Mar, 2 Mar to 26 Apr, 26 Apr to 1 Jul. Each block is predicted by a model built on the other two. The cuts fall on days with no labelled event in progress, so no event is split between training and validation. With only 29 events, training only on the past would leave the first block with almost nothing to learn from.

Training labels: the 28 work orders plus the stuck flap of B1-AHU-11 that I found in `notebooks/04_faults.ipynb` (22 to 30 April, `EXTRA_LABELS` in `config.py`).

## Features

`src/ahu_fdd/features.py` builds the signals below. Each one comes from the fingerprint of a fault (`notebooks/04_faults.ipynb`) or from how a healthy machine behaves (`notebooks/03_patterns.ipynb`). Here they are grouped by what they are for. **The model uses only the 9 marked "in the model"** (`MODEL_FEATURES`): the ones compared with each machine's own normal, plus the share of outdoor air. The others are used by the rules or kept as context (see below why).

**1. Context: what situation the machine is in.** They don't find faults on their own. Not in the model (see "Why only relative features").

| Feature | What it is | Why |
|---|---|---|
| `minutes_on` | Minutes since the fan started | The first 30 minutes look like a fault and are not |
| `oat_c` | Outside air temperature | When it's hotter, everything works harder |
| `oat_change_1h` | Change in outside air over the last hour | Catches storms, which move the valve with no fault |
| `fan_speed_pct` | Fan speed | How much air the machine moves |
| `chw_valve_cmd_pct` | Valve command now | The "accelerator" of the cooling |
| `oa_damper_cmd_pct` | Flap command now | How much outdoor air is asked for |

**2. Stuck tap** (`chw_valve_stuck`): **the supply air goes off target and the valve command runs to a limit.**

| Feature | What it is |
|---|---|
| `sat_error_1h`, `sat_error_3h` (raw, not in the model) | How far the supply air is from its setpoint, median of the last 1 and 3 hours |
| `sat_error_dev` (in the model) | That error compared with this machine's normal (for the three machines always at their limit) |
| `valve_at_limit_1h` (in the model) | Share of the last hour with the valve command at 0% or 100% |
| `valve_1h`, `valve_dev` (in the model) | Valve command over the last hour, and how much more open than this machine's normal |

**3. Stuck flap** (`oa_damper_stuck`): **no outdoor air comes in and CO2 goes up.**

| Feature | What it is |
|---|---|
| `oa_fraction_1h` (in the model) | Share of outdoor air in the mix (mixing formula), last hour |
| `oa_fraction_dev` (in the model) | That share compared with this machine's normal |
| `damper_dev` (in the model) | How much more the flap is asked to open than usual (the controller tries to compensate) |
| `co2_dev` (in the model) | CO2 above this machine's normal (office and hospital only) |

**4. Weak radiator** (`low_coil_capacity`): **the machine needs more valve for the same work.**

| Feature | What it is |
|---|---|
| `valve_excess` (in the model) | How much more the valve is open than this machine usually needs for the same cooling work (fan speed share times °C cooled), last 3 hours. Like a car with a weak engine: you press the accelerator more to go at the same speed |
| `cooling_per_valve_3h` | Cooling per % of valve over the last 3 hours. The simple version, not in the model |

Why `valve_excess` and not only "cooling per % of valve": a valve is not linear, it gives less cooling per % when it is very open (on B2-AHU-10, about 35 °C per 100% of valve at 20% open, and 13 °C at 90% open). My first rule compared with one fixed value per machine and raised almost one false alarm per machine per week, every hot afternoon. Asking "how much valve does this machine need for this work" fixed it without losing any fault. In healthy rows the valve is almost never more than 3 points above what it needs; during a weak radiator, about 20 points.

**5. Lying thermometer** (`sat_sensor_bias`): **the check at rest.**

| Feature | What it is |
|---|---|
| `rest_offset_dev` (in the model) | At the last stop (fan off for an hour), how far the supply sensor was from the mixed air sensor, compared with this machine's normal. Kept for 48 hours, so it can be used while the machine runs |

**Why only relative features.** I first gave the model all the signals, raw values included (supply air error, valve opening, outside air, fan speed). It got the fault type right in 69% of the events (and missed 3 of the 29 faults). The three machines that are always at their limit (B1-AHU-05, B3-AHU-02, B3-AHU-09) have raw values that always look like a stuck tap, so the model mixed them up. With only the signals compared with each machine's own normal, the right type went up to 86%, with every fault still found. So the model sees "how far is this machine from its own normal", never "what is the value".

**Three ideas behind all of them:**
1. Smoothed over 1 to 3 hours, so a storm or a single odd reading doesn't count.
2. Compared with each machine's own normal (`ahu_baselines()` and `valve_curve()`, built only from healthy rows of the training data), because machines differ a lot.
3. Start-up rows (first 30 minutes) are left out of the calculations.

Empty values are allowed: no CO2 in the mall (no sensor), no check at rest in the 24/7 machines (they never stop), and the frozen sensor in test (set to empty in notebook 02). LightGBM handles empty values on its own, which is one of the reasons to use it.

## Rules baseline

One physics rule per fault (`src/ahu_fdd/rules.py`, thresholds in `config.py`), then alarms shorter than 2 hours of running are dropped (`src/ahu_fdd/postprocess.py`):

| Fault | Rule |
|---|---|
| Stuck tap | Supply air more than 2.5 °C off this machine's normal, and the valve command at 0% or 100% most of the last hour |
| Stuck flap | Almost no outdoor air (fraction under 0.03), at least 0.05 below this machine's normal |
| Lying thermometer | Last check at rest more than 1.5 °C away from this machine's normal |
| Weak radiator | Valve more than 10 points above what this machine needs for the same work, supply air on target |

When several rules fire, the clearest fault wins: stuck tap, stuck flap, lying thermometer, weak radiator.

Result over the three validation blocks (29 events):

| Version | Detected | Right type | Median delay | False alarms per AHU per month |
|---|---|---|---|---|
| Weak radiator vs one fixed value | 100% | 93% | 11 h | 4.7 |
| Weak radiator vs valve needed for the work | 100% | 93% | 11 h | 0.20 |

The two wrong types are weak radiators in machines that are always at their limit (B1-AHU-05, B3-AHU-02), called stuck tap by the rules. Notebook 04 already showed these would be hard.

After adding the step that joins the pieces of one fault (below), the rules give 0.18 false alarms per AHU per month.

## How I framed the problem

The options are a classifier, a model of normal behaviour with residuals, rules, or a mix. I used a mix:
- **Residuals:** every feature is "how far this machine is from its own normal" (second framing).
- **A LightGBM classifier decides *if* there is a fault.** It gives the fewest false alarms.
- **The physics rules decide *which* fault.** They get the type right more often.

Everyday example: a nurse takes your temperature and decides if you see the doctor; the doctor decides what you have.

## Why LightGBM and not another model

- The problem is tabular and threshold-like ("supply air off *and* valve at 100%"): gradient boosted trees learn exactly this kind of rule, and combinations of them.
- It handles empty values on its own: no CO2 in the mall, no check at rest on 24/7 machines, the frozen sensor in test. Other models need invented values.
- Class weights handle the imbalance without inventing rows (no SMOTE: copied fault rows would also leak between training and validation).
- It is fast on 2 million rows, and feature importance shows what each alarm is based on.
- With only 29 events, the features matter more than the model. I keep it small on purpose (shallow trees, at least 200 rows per leaf, `LGBM_PARAMS` in `config.py`) so it can't learn the 29 events by heart.

Other options, and why not:

| Model | Why not as the main model |
|---|---|
| Logistic regression | Can't combine signals ("error *and* valve at a limit") and needs invented values for empty cells. In validation: 76% found, 59% right type |
| Random forest | Same family idea, but in validation it missed 2 of the 29 faults and got fewer types right (79%) |
| XGBoost, CatBoost, scikit-learn HistGradientBoosting | Same family as LightGBM: I expect almost the same result. Worth a comparison with more time |
| Neural networks (LSTM and similar) | 29 events are far too few to train them without learning them by heart |
| Anomaly detection only (Isolation Forest, autoencoder) | Says "something is odd" but not which fault, and I need the type. It also tends to give more false alarms |

## From rows to alarms

The model predicts each 5-minute row. A technician gets alarms. `src/ahu_fdd/postprocess.py`:
1. No alarms with the fan off or in the first 30 minutes after a start.
2. A row is a fault only if the model is at least 80% sure (`ALARM_MIN_PROB`).
3. Alarms shorter than 2 hours of running are dropped (flicker, storms).
4. Alarms of one machine split only by a short gap (up to 6 hours of running, like the morning start-up) become one alarm. Without this, a 17-day fault became 18 daily alarms.
5. One type per alarm: the type the physics rules give inside the alarm, or the model's type if no rule fires.

## Results

Three validation blocks, 29 events, about 240 machine-months. Same post-processing for every option.

| Option | Found | Right type | Median delay | False alarms per AHU per month |
|---|---|---|---|---|
| Physics rules | 100% | 93% | 11 h | 0.18 |
| Logistic regression | 76% | 59% | 4 h | 1.48 |
| Random forest | 93% | 79% | 11 h | 0.03 |
| LightGBM | 100% | 86% | 10 h | 0.05 |
| **LightGBM + rule types (final)** | **100%** | **93%** | **10 h** | **0.05** |

0.05 false alarms per machine per month is about one per machine every 20 months.

## What I tried

Three tests behind the final settings, re-run in `notebooks/05_modelling.ipynb` (section 4, "What I tried") with the same validation and scorer:

| Test | Options | Result | Decision |
|---|---|---|---|
| A. Model features | all signals (raw + relative) vs relative only | relative only: more faults found and more right types (the machines at their limit stop looking like a stuck tap) | 9 relative features (`MODEL_FEATURES`) |
| B. How sure the model must be | 50%, 70%, 80%, 90% | 80% cuts most false alarms and still finds every fault; 90% starts to miss faults | `ALARM_MIN_PROB = 0.8` |
| C. Join the pieces of one fault | not joined, under 2 h apart, under 6 h apart | fewer alarms for the same faults; joining never adds false alarms | `MAX_GAP_ROWS = 72` (6 h of running) |
| D. CO2 hidden in half the training rows | to help buildings with no CO2 sensor | no better on the mall | not used |

The exact numbers are in the notebook, so they always match the code.

**Error analysis.**
- Wrong types: only the weak radiators of B1-AHU-05 and B3-AHU-02, called stuck tap. On these machines the valve is at 100% on a normal day, so a weak coil can't make it open more, and warm supply air is also the sign of a stuck tap. A valve position sensor or a chilled water flow meter would separate them.
- False alarms: all in the mall, all 2 to 5 hours of running, half of them weak radiators on the machines at their limit on hot afternoons. A longer minimum alarm for faults that can wait (lying thermometer, weak radiator) and the technicians' "no fault found" feedback as labels would cut them.
- The lying thermometer is found the first night after it starts (the check needs the fan off), so up to a day late. On 24/7 machines it can't be seen at all with these sensors.

## A new AHU, and a building with fewer sensors

I hid a whole building: the model is trained on the other two, and the hidden building gets no labels. Its normal comes from its first two weeks of data, treated as healthy.

| New building | Physics rules | Final model |
|---|---|---|
| B1 office | 100% found, 89% type, 0.02 FA | 100%, 89%, 0.05 FA |
| B2 hospital | 100%, 100%, 0.02 FA | 50%, 50%, 0.00 FA |
| B3 mall (no CO2, no airflow) | 100%, 92%, 0.58 FA | 58%, 50%, 1.11 FA |

The model doesn't transfer well to a building it never saw: it learned the stuck flap mostly through CO2 (the mall has none), and 5 of the 6 lying thermometers are in the mall. The rules need no examples, only physics.

**So, for a new AHU or building:**
1. Weeks 1-2: collect data, no alarms, learn each machine's normal.
2. From week 3: physics rules only. They work with the sensors the building has.
3. Once the building has its own confirmed work orders: retrain the model with them and switch to the combination.

**Fewer sensors:** all features may be empty and the rules don't depend on the missing ones (without CO2, a stuck flap still shows in the outdoor air share). Hiding CO2 in half of the training rows did not make the model transfer better. With more buildings, I would train one model per sensor set.

## Test period

`python -m ahu_fdd.predict` trains on January to June and writes `predictions.csv` (711,994 rows, with its format checked by `format_problems()`). It raises 14 alarms in 40 machines over July and August. They include the eight candidates I saw by hand in notebook 04 (same type and dates), two weak radiators I couldn't look for by hand, and no alarm on B2-AHU-08, whose supply air sensor is frozen for 9 days.

## Model card

Every run of `python -m ahu_fdd.predict` saves the trained model and its card in `artifacts/lgbm-v<version>/`:

- `model.txt`: the LightGBM model in its text format (it can be opened, read and loaded without training again).
- `model_card.json`: the package version, the git commit of the code (and whether the code had uncommitted changes), when it was trained, the training period, the number of fault events (work orders and extra labels), the features, the LightGBM parameters, the alarm settings, the validation scores and the number of test alarms.

So every `predictions.csv` can be traced back to the exact model, code and data that made it. This is a small, local version of a model registry: in production the same information goes to MLflow, and a new model (challenger) only replaces the current one (champion) if it beats it on the same validation. See the architecture section of the report.

## Fault simulator

`app/` has a small Streamlit app to play with the model: inject one of the four faults into a healthy AHU, with the size and dates you choose, and see the signal, the model's confidence and the alarms, scored by event. The physics of each injected fault is in `src/ahu_fdd/simulate.py` (with tests), and the app uses the same pipeline as `predictions.csv` (`fit_pipeline()` once, then `predict_alarms()`). How to run and use it: `app/README.md` and Appendix F of the report.

## How small a fault can it catch?

The labelled events only show the sizes that happened. So I add simulated faults to healthy machines, from small to clear, with `sensitivity_table()` in `src/ahu_fdd/simulation.py`. It is like testing a smoke alarm with more and more smoke. The test runs 14 days from Monday 4 August: 3 healthy days, then 7 days of fault. The model never saw these months. Each machine also has a control run with no fault, and all of them were clean.

| Fault | Size | B1-AHU-02 (office) | B2-AHU-03 (hospital, 24/7) | B3-AHU-07 (mall) |
|---|---|---|---|---|
| Stuck tap (`chw_valve_stuck`) | Real valve position, 0 to 40% | From 30% | All sizes | All sizes |
| Stuck flap (`oa_damper_stuck`) | Outdoor air left, 0 to 40% | All sizes | All sizes | All sizes |
| Weak radiator (`low_coil_capacity`) | Capacity left, 90 to 50% | All sizes, 128 h late at 90% | From 80% | From 70% |
| Lying thermometer (`sat_sensor_bias`), too high | 0.5 to 3 °C | From 1 °C | Only 3 °C, wrong type | From 1.5 °C, right type from 2 °C |
| Lying thermometer (`sat_sensor_bias`), too low | -0.5 to -3 °C | From -1.5 °C | None | From -1 °C |

What I learn from it:

- The stuck flap is found at every size I tried. The stuck tap is too, except a valve stuck at 40% on the office machine.
- The hospital machine shows the blind spot in numbers: it never stops, so there is no check at rest, and a lying thermometer stays hidden. This agrees with notebook 04 and with Appendix E of the report.
- The small weak radiator is the slow case. With 10% of capacity lost, one machine needed 128 hours and two were not found.

Limits: three machines, one window, and simple simulated physics. The faults start at once, and on the 24/7 machine the alarm can start in the first hour. A real fault that grows slowly would take longer. This is a guide, not a measured detection limit.

## With more time

- Compare XGBoost and CatBoost, and tune the model with more care.
- A two-step model: first "is there a fault?", then "which one?".
- Use the unlabelled data (self-training on confident alarms).
- Ask the operator for the technicians' "no fault found" outcomes, to measure false alarms on real visits.
