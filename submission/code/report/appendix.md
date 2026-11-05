# Appendix

Details behind the main pages. Not needed to follow the report.

## A. Why I answered the client this way (Question 4)

**The reply to the facilities manager.** They are not technical, they are frustrated, and they have to tell the owner something. So I followed five rules:

1. **Acknowledge first, defend later.** Their point is correct: alerts that technicians ignore are worthless. Saying so in the first lines, in a professional tone, keeps the conversation open.
2. **No blame, and no guilt I can't prove yet.** "Nothing found" doesn't always mean "nothing broken": some faults can't be seen without the right test (Q1: a supply air sensor bias is invisible while the machine runs). Instead of saying whose fault it was, the reply turns this into an action: during the review I send a "what to check" note with each alert. I keep it manual on purpose: turning it into a product feature may be outside the agreed scope, so it goes to the project lead as a possible change request, not as a promise to the client.
3. **Plain words and one example per idea.** No model, threshold or feature. "A unit that is a bit small for its area" is the healthy machine at its limit of Q1; "a sensor that reads 2 degrees too high" is the sensor bias.
4. **Concrete actions with a date,** small enough to do this week and inside the current scope: review of the 9 alerts by Wednesday, only high-confidence alerts, a "what to check" note with each alert, a joint visit.
5. **Give them a message for the owner** that keeps the owner's timeline but protects the technicians: connect the new buildings next month without alerts, and turn alerts on when a clear target is met. A yes/no answer would put the facilities manager in a bad position.

**The internal note.** Here I can be direct and use numbers. Every hypothesis comes from what I saw in the data:

| Hypothesis in the note | Where it comes from |
|---|---|
| Alerts turned on too early in a new building | Q2: a model trained on other buildings found about half of the faults of a building it never saw; the rules found all of them |
| Healthy machines that look faulty | Q1: 3 of 40 units always run at full valve and look like a weak coil, labelled normal by the client |
| A data problem | Q1: each building had its own problem (clock shift, repeated day, outage, wrong units, frozen sensors) |
| Real faults hard to confirm on site | Q1: the sensor bias only shows with the fan off |
| 9 alerts is about ten times the expected rate | Q2: 0.05 false alarms per AHU per month in validation, so less than one a month for 12-16 units |

**The rollout recommendation.** I didn't say "go" or "stop". Connecting the new buildings in shadow mode costs nothing in trust and gains time, because each machine needs about two weeks of data to learn its normal anyway (Q3, onboarding). The target (7 of 10 checked alerts confirmed, two weeks in a row) is simple enough for the owner to follow, and the four-week limit makes sure we don't hide the problem if it doesn't improve.

## B. Model details (Question 2)

**The 9 features.** Each one is compared with the same machine's normal, learned from its healthy rows.

| Feature | What it measures | Mainly for |
|---|---|---|
| `sat_error_dev` | Supply air minus setpoint, last hour, vs this machine's usual error | Stuck valve |
| `valve_dev` | Valve command, last hour, vs this machine's usual opening | Stuck valve |
| `valve_at_limit_1h` | Share of the last hour with the valve command at 0% or 100% | Stuck valve |
| `valve_excess` | Valve above what this machine needs for the same cooling work (fan speed × °C cooled), last 3 hours | Low coil capacity |
| `oa_fraction_1h` | Outdoor air share from the mixing formula, last hour | Stuck damper |
| `oa_fraction_dev` | The same share vs this machine's normal | Stuck damper |
| `damper_dev` | Damper command above its usual value (the controller compensates) | Stuck damper |
| `co2_dev` | CO2 above this machine's normal (office and hospital only) | Stuck damper |
| `rest_offset_dev` | Last check with the fan off for an hour: supply minus mixed air, vs normal | Sensor bias |

**The tests behind the final settings** (same validation and scorer as the main table):

| Test | Option | Alarms raised | Found | Right type | False alarms per AHU-month |
|------------------|------------------------|------|------|------|------|
| A. Features (model alone) | Raw + relative signals | 50 | 90% | 69% | 0.04 |
| | **Relative signals only** | 52 | 100% | 86% | 0.05 |
| B. Confidence | 50% | 128 | 100% | 93% | 0.36 |
| | 70% | 67 | 100% | 93% | 0.11 |
| | **80%** | 52 | 100% | 93% | 0.05 |
| | 90% | 38 | 93% | 86% | 0.01 |
| C. Join pieces of a fault | Not joined | 193 | 100% | 93% | 0.05 |
| | Under 2 hours apart | 70 | 100% | 93% | 0.05 |
| | **Under 6 hours apart** | 52 | 100% | 93% | 0.05 |

- **A:** with raw values, the three machines always at their limit look like a stuck valve, so the model misses faults and mixes types.
- **B:** 80% is the highest confidence that still finds every fault.
- **C:** joining the pieces of one fault (the morning start-up cut them) gives fewer alarms for the same faults; it never adds false alarms.

**Right type per fault (final model):** stuck valve 100%, stuck damper 100%, sensor bias 100%, low coil capacity 71% (the two errors are the machines at their limit).

## C. Alarms in the test period

The 14 alarms in `predictions.csv` (July and August), from the first to the last hour of each:

| AHU | Fault | From | To | Days |
|------------|------------------------|--------------------|--------------------|------|
| B3-AHU-11 | `sat_sensor_bias` | Wed 02 Jul 13:05 | Wed 02 Jul 16:50 | 0.2 |
| B1-AHU-01 | `chw_valve_stuck` | Mon 07 Jul 15:15 | Fri 11 Jul 19:25 | 4.2 |
| B1-AHU-03 | `low_coil_capacity` | Wed 09 Jul 14:15 | Fri 11 Jul 19:25 | 2.2 |
| B3-AHU-05 | `sat_sensor_bias` | Sat 12 Jul 10:30 | Sat 12 Jul 12:35 | 0.1 |
| B2-AHU-12 | `oa_damper_stuck` | Sat 12 Jul 16:40 | Thu 24 Jul 15:25 | 11.9 |
| B1-AHU-09 | `low_coil_capacity` | Tue 15 Jul 09:05 | Fri 18 Jul 11:25 | 3.1 |
| B1-AHU-12 | `sat_sensor_bias` | Tue 22 Jul 08:05 | Wed 06 Aug 19:25 | 15.5 |
| B3-AHU-05 | `chw_valve_stuck` | Tue 22 Jul 09:45 | Tue 29 Jul 22:55 | 7.5 |
| B1-AHU-16 | `chw_valve_stuck` | Wed 23 Jul 09:30 | Mon 28 Jul 17:30 | 5.3 |
| B3-AHU-06 | `sat_sensor_bias` | Fri 25 Jul 09:30 | Mon 11 Aug 20:40 | 17.5 |
| B3-AHU-03 | `low_coil_capacity` | Sat 26 Jul 15:25 | Sat 26 Jul 19:00 | 0.1 |
| B3-AHU-03 | `low_coil_capacity` | Sun 27 Jul 11:25 | Mon 28 Jul 17:55 | 1.3 |
| B2-AHU-07 | `oa_damper_stuck` | Wed 30 Jul 00:10 | Tue 05 Aug 06:50 | 6.3 |
| B3-AHU-01 | `oa_damper_stuck` | Thu 21 Aug 09:45 | Tue 26 Aug 20:50 | 5.5 |

Eight of them (stuck valves on B1-AHU-01, B1-AHU-16 and B3-AHU-05; stuck dampers on B2-AHU-07, B2-AHU-12 and B3-AHU-01; sensor bias on B1-AHU-12 and B3-AHU-06) match the fingerprints I could see by hand in the data before training. The short ones (under a day) look like the false alarms of validation. B2-AHU-08, whose supply air sensor is frozen for 9 days, has no alarm.

## D. Questions for the client

All in one list, from the data work and the design (also in `code/docs/decisions.md`):

1. Did the office BMS change its time settings in early June? Was the mall data joined from overlapping exports? Was the hospital BMS down from 10 to 18 March?
2. Was a meter changed on B3-AHU-04 in April? Why did the return air sensor of B1-AHU-07 and the supply air sensor of B2-AHU-08 stop updating?
3. Was there a work order for B1-AHU-11 at the end of April (stuck damper in the data, none in the labels)?
4. Are B1-AHU-05, B3-AHU-02 and B3-AHU-09 known to be undersized?
5. Where are the buildings, and which holiday calendar do they follow (I assumed Singapore)?
6. Can technicians close each alert with "fault confirmed" or "no fault found"?
7. Can each edge PC reach one HTTPS endpoint, and how much trend history does each BMS keep?

## E. If I had more time

In order of what I think would help the client most:

1. **Cold start: a new building with no labels.** Today a new building runs on the physics rules until it has its own confirmed work orders, because the model trained on other buildings found only 50-60% of the faults in a building it never saw. To shorten that time:
    - **Inject faults into healthy data.** Take a healthy machine of the new building and simulate each fault in its own data (hold the valve, close the damper, add 2 °C to the supply sensor, cut the coil capacity), with a known start and size. The model gets labelled examples from day one, and I can measure the detection delay on each building before going live.
    - **Train on more general signals.** Most features are already relative to each machine; adding the building type and the sensors fitted as features, and training across buildings with more of them, should make the model transfer better.
    - **Ask for the right labels first.** Send the technicians first the alerts where the model is least sure, so each visit teaches the model as much as possible (active learning).
2. **Sensor bias on 24/7 machines.** The check at rest needs the fan off, so it can't run on the hospital. Options: a short planned stop at night once a week, or a "virtual sensor" that estimates the supply air from the chilled water temperatures and the valve, and compares it with the real sensor.
3. **Explain each alert and recommend an action.** For every alarm: the two or three signals behind it (feature contributions) and a plain "what to check on site" line per fault type. This is the change request of Question 4: it would help the technicians most.
4. **Severity by cost.** Estimate the energy wasted by each fault (cooling lost or extra fan and valve work, in kW) and rank alerts by money and comfort, not only by fault type.
5. **Separate the hard pair.** A stuck valve and a low coil capacity look alike on the machines at their limit. A valve position feedback signal or a chilled water flow meter on those three units would remove most of the type errors.
6. **More model options and tuning.** Compare XGBoost and CatBoost, tune the parameters inside the time blocks, try a two-step model (fault yes or no, then which one), and calibrate the probabilities so "80% sure" really means 80%.
7. **Use the unlabelled data.** Self-training on very confident alarms, and an automatic check of every work order against its fingerprint, to find missing labels like B1-AHU-11 and wrong dates.
8. **Production pieces of Question 3 in code.** MLflow with the champion and challenger rule (two gates), a Dockerfile, and the data quality gate (pass, warn, block) as a job.

## F. How to reproduce

From `code/` (details in `code/README.md`):

```bash
pip install -r requirements.txt && pip install -e .
python -m ahu_fdd.predict          # rebuilds predictions.csv and the model card (about 1 minute)
pytest -q --cov                    # 54 unit tests
python report/build.py             # rebuilds this report (needs pandoc and tectonic)
```

