# Fault simulator

A small Streamlit app to play with the model: pick a healthy AHU, inject one of the four faults with the size you want, and see if and when an alarm is raised.

## Run it

From `submission/code/`, after the setup of the main README (the data must be in `../../assignment/data/` or in `AHU_DATA_DIR`):

```bash
pip install -r app/requirements-app.txt
streamlit run app/streamlit_app.py
```

It opens in the browser. The first load trains the model on January to June (about 30 seconds); after that every change takes one or two seconds.

## What you can change (sidebar)

1. **Machine and period:** any of the 40 AHUs, and the first of the 14 days shown (train or test period).
2. **Fault to inject:** none, stuck tap (`chw_valve_stuck`), stuck flap (`oa_damper_stuck`), lying thermometer (`sat_sensor_bias`) or weak radiator (`low_coil_capacity`); the day it starts, how long it lasts and its size (valve position, outdoor air left, sensor bias in °C, coil capacity left).
3. **Alarm settings:** the model confidence needed, the minimum alarm length and the gap to join alarms. The defaults are the ones used for `predictions.csv`.

## What you see

- **Detected, delay, type, false alarms:** the same event-level scoring as the brief.
- **Chart 1:** the signal that shows the fault, healthy (grey) and with the fault (blue). The shaded band is the fault.
- **Chart 2:** how sure the model is that something is wrong, with the confidence needed as a dashed line.
- **Chart 3:** the alarms a technician would get, coloured by fault type.

Tip: choose "No fault" and lower the confidence to see how false alarms appear; choose a fault and shrink its size to find the smallest fault the model still catches.

## Files

| File | What it does |
|---|---|
| `streamlit_app.py` | The page: sidebar, numbers and charts |
| `simulation.py` | The simulation without the page: load and train once, inject, run the pipeline, score |
| `example_figure.py` | Draws the example of the report (`figures/simulator_example.png`) with the same simulation |
| `requirements-app.txt` | Streamlit, only needed for the app |

The physics of each injected fault is in `src/ahu_fdd/simulate.py` (with unit tests). It is simple on purpose: each fault changes the sensors the way the labelled events of notebook 04 show, not a full model of the AHU.
