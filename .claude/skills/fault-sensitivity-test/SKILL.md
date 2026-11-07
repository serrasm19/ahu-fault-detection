---
name: fault-sensitivity-test
description: Measure how small a fault the AHU detector can still catch, by injecting simulated faults of several sizes into healthy machines and scoring each run. Use this whenever someone asks how sensitive the model is, what the smallest detectable fault is, whether a change in settings hurt detection, how long detection takes for a small fault, or wants a what-if test with a simulated fault.
---

# Fault sensitivity test

The labelled events show only the fault sizes that happened. This test adds simulated faults to healthy data, from small to clear, and shows where the detector stops finding them.

## Steps

Run from the repository root with the project environment. It takes about a minute to load and train, then a few seconds per run.

1. **Choose the test.** The fault, and at least one machine per building that the question touches. One machine says little, because machines differ a lot.

   | Fault | What the size means | Default sizes, small to clear |
   |---|---|---|
   | `chw_valve_stuck` | Real valve position, % | 40, 30, 20, 10, 0 |
   | `oa_damper_stuck` | Outdoor air left, % | 40, 30, 20, 10, 0 |
   | `sat_sensor_bias` | Sensor error, °C | 0.5, 1, 1.5, 2, 3 |
   | `low_coil_capacity` | Coil capacity left, % | 90, 80, 70, 60, 50 |

   A sensor can read high or low, so test both signs for `sat_sensor_bias`.

2. **Choose the window.** Use the test period (July and August), because the model never saw it. The run covers 14 days from `--start`: 3 healthy days, then 7 days of fault. `--list` in the `ahu-alarm-triage` script shows the alarms to avoid.

3. **Run it:**

   ```bash
   .venv/bin/python .claude/skills/fault-sensitivity-test/scripts/run_sweep.py --ahus B1-AHU-02,B2-AHU-03,B3-AHU-07 --fault sat_sensor_bias --start 2025-08-04
   ```

   For negative sizes write `--sizes=-1,-2,-3`.

4. **Check the control first.** The first row of each machine has no fault. If it has a false alarm, that window was not healthy and the rows of that machine can't be trusted. Pick another window or machine and run it again.

5. **Report it** with the format below.

## Report format

```markdown
**Question:** <what was tested>
**Answer:** <smallest size found on all machines, in one sentence>

<table: machine, size, found, delay in hours, right type, false alarms>

**What I see:** <where detection stops, and how delay and type change with size>
**Limits:** <see below>
```

## Limits to state

- The faults are simulated with simple physics (`src/ahu_fdd/simulate.py`). The result is a guide, not a measured detection limit.
- It covers only the chosen machines and window.
- Size 100% on capacity, or the normal position on a valve, is no fault. Don't read a miss there as a failure.
- A lying thermometer can only show on machines that switch off, so don't test it on a 24/7 machine and call the result a model failure. Say it is a known blind spot.

If the user wants to see one run in charts, point them to the fault simulator app: `streamlit run app/streamlit_app.py` from `project/code/`.
