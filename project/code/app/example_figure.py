"""Draw one simulator example for the report: python app/example_figure.py (from code/)

Same simulation as the app (ahu_fdd/simulation.py): a stuck valve in a healthy office AHU.
"""

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from ahu_fdd.config import ALARM_MIN_PROB, FAULT_NAMES, MAX_GAP_ROWS, MIN_ALARM_ROWS
from ahu_fdd.plots import FAULT_COLORS, save_fig, set_style
from ahu_fdd.simulation import load_pipeline, simulate

# The example: B1-AHU-02 (office), valve stuck at 10% for 4 days from Wednesday 9 July
AHU, WINDOW_START = "B1-AHU-02", pd.Timestamp("2025-07-07")
FAULT, FAULT_START, FAULT_END, SIZE = "chw_valve_stuck", "2025-07-09", "2025-07-13", 10.0

set_style()
fitted, data, _ = load_pipeline()
result = simulate(
    fitted,
    data,
    ahu_id=AHU,
    window_start=WINDOW_START,
    fault=FAULT,
    fault_start=pd.Timestamp(FAULT_START),
    fault_end=pd.Timestamp(FAULT_END),
    size=SIZE,
    min_prob=ALARM_MIN_PROB,
    min_alarm_rows=MIN_ALARM_ROWS,
    max_gap_rows=MAX_GAP_ROWS,
)
times = result.after["timestamp"].dt.floor("h")

fig, axes = plt.subplots(3, 1, figsize=(10, 6), sharex=True, height_ratios=[2, 1.4, 0.6])
for ax in axes:
    ax.axvspan(pd.Timestamp(FAULT_START), pd.Timestamp(FAULT_END), color="#eb6834", alpha=0.12)

# 1. The signal that shows the fault, healthy vs with the fault (hourly median, running only)
for frame, label, color in [
    (result.before, "healthy", "#9a9893"),
    (result.after, "with the fault", "#2a78d6"),
]:
    axes[0].plot(
        frame["sat_error_run"].groupby(times).median(), ".", ms=3, color=color, label=label
    )
axes[0].set_ylabel("Supply air minus\nsetpoint (°C)")
axes[0].legend(loc="upper right")

# 2. How sure the model is, with the confidence needed for an alarm
axes[1].plot(result.fault_probability.groupby(times).median(), color="#8a5cd6")
axes[1].axhline(ALARM_MIN_PROB, ls="--", color="black", lw=0.8)
axes[1].set_ylabel("Fault\nprobability")
axes[1].set_ylim(0, 1.05)

# 3. The alarms a technician would get
for alarm in result.events.itertuples():
    axes[2].axvspan(
        alarm.start, alarm.end, ymin=0.2, ymax=0.8, color=FAULT_COLORS[alarm.fault_type]
    )
axes[2].set_yticks([])
axes[2].set_ylabel("Alarms")
axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
axes[2].set_xlim(WINDOW_START, WINDOW_START + pd.Timedelta(days=14))

found = (
    f"found after {result.delay_h:.0f} h as {FAULT_NAMES[result.main_type]}"
    if result.detected
    else "not found"
)
fig.suptitle(f"Simulator example: {AHU}, valve stuck at 10% (shaded), {found}", y=1.0)
fig.tight_layout()
save_fig(fig, "simulator_example")
print(f"saved: {found}, false alarms {result.false_alarms}")
