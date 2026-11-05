# Modelling

Back to the [project map](00%20-%20Project%20map.md).

Work in progress (phase 2). This note grows with each step.

## How I score a model

In plain words: before the real exam (July and August, scored by the client), I do practice exams on January to June, where I know the answers, and I mark them with the same rules the client uses. Without this, every model choice would be a guess.

The client scores by fault event, not by row (a model that always says "normal" is right on 97.6% of the rows and useless). `src/ahu_fdd/evaluation.py` copies what the brief describes, on fan-on rows only:

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

The model uses 19 features (`MODEL_FEATURES` in `src/ahu_fdd/features.py`). Each one comes from the fingerprint of a fault (`notebooks/04_faults.ipynb`) or from how a healthy machine behaves (`notebooks/03_patterns.ipynb`). Here they are grouped by what they are for.

**1. Context: what situation the machine is in.** They don't find faults on their own, but they stop the model from mixing up normal changes with faults.

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
| `sat_error_1h`, `sat_error_3h` | How far the supply air is from its setpoint, median of the last 1 and 3 hours |
| `sat_error_dev` | That error compared with this machine's normal (for the three machines always at their limit) |
| `valve_at_limit_1h` | Share of the last hour with the valve command at 0% or 100% |
| `valve_1h`, `valve_dev` | Valve command over the last hour, and how much more open than this machine's normal |

**3. Stuck flap** (`oa_damper_stuck`): **no outdoor air comes in and CO2 goes up.**

| Feature | What it is |
|---|---|
| `oa_fraction_1h` | Share of outdoor air in the mix (mixing formula), last hour |
| `oa_fraction_dev` | That share compared with this machine's normal |
| `damper_dev` | How much more the flap is asked to open than usual (the controller tries to compensate) |
| `co2_dev` | CO2 above this machine's normal (office and hospital only) |

**4. Weak radiator** (`low_coil_capacity`): **the machine needs more valve for the same work.**

| Feature | What it is |
|---|---|
| `valve_excess` | How much more the valve is open than this machine usually needs for the same cooling work (fan speed share times °C cooled), last 3 hours. Like a car with a weak engine: you press the accelerator more to go at the same speed |
| `cooling_per_valve_3h` | Cooling per % of valve over the last 3 hours. The simple version, kept as support |

Why `valve_excess` and not only "cooling per % of valve": a valve is not linear, it gives less cooling per % when it is very open (on B2-AHU-10, about 35 °C per 100% of valve at 20% open, and 13 °C at 90% open). My first rule compared with one fixed value per machine and raised almost one false alarm per machine per week, every hot afternoon. Asking "how much valve does this machine need for this work" fixed it without losing any fault. In healthy rows the valve is almost never more than 3 points above what it needs; during a weak radiator, about 20 points.

**5. Lying thermometer** (`sat_sensor_bias`): **the check at rest.**

| Feature | What it is |
|---|---|
| `rest_offset_dev` | At the last stop (fan off for an hour), how far the supply sensor was from the mixed air sensor, compared with this machine's normal. Kept for 48 hours, so it can be used while the machine runs |

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

Next: a LightGBM model on the same features, which has to beat these rules to be worth it.
