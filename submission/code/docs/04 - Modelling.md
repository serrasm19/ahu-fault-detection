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

From the fingerprints of `notebooks/04_faults.ipynb`, in `src/ahu_fdd/features.py`:

- Smoothed over 1 and 3 hours, so a storm or a single odd reading doesn't count. Start-up rows (first 30 minutes) are left out.
- Compared with each machine's own normal (`ahu_baselines()`), because machines differ a lot (notebook 03).
- The last check at rest (supply minus mixed air with the fan off) is carried to the next 48 hours of running, for the lying thermometer.
- `valve_excess`: how much more the valve is open than this machine usually needs for the same cooling work (fan speed share times °C cooled). This is the weak radiator signal.

Why `valve_excess` and not a simple "cooling per % of valve": a valve is not linear, it gives less cooling per % when it is very open. My first rule compared with one fixed value per machine and raised almost one false alarm per machine per week, every hot afternoon. Asking "how much valve does this machine need for this work" fixed it without losing any fault.

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
