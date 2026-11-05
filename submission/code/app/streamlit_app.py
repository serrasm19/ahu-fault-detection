"""Fault simulator: inject a fault into a healthy AHU and see if and when an alarm is raised.

Run from submission/code/:  streamlit run app/streamlit_app.py
"""

import altair as alt
import pandas as pd
import streamlit as st
from simulation import WINDOW_DAYS, load_pipeline, simulate

from ahu_fdd.config import ALARM_MIN_PROB, FAULT_NAMES, MAX_GAP_ROWS, MIN_ALARM_ROWS, NORMAL
from ahu_fdd.plots import FAULT_COLORS
from ahu_fdd.simulate import FAULT_SIZES

ROWS_PER_HOUR = 12  # 5-minute data

# The signal that shows each fault best (notebook 04), and how to name it in the chart.
# The "_run" columns only keep rows with the machine running after start-up (add_features)
KEY_SIGNAL = {
    NORMAL: ("sat_error_run", "Supply air minus setpoint (°C), running"),
    "chw_valve_stuck": ("sat_error_run", "Supply air minus setpoint (°C), running"),
    "oa_damper_stuck": ("oa_fraction_run", "Outdoor air share in the mix, running"),
    "sat_sensor_bias": ("rest_offset", "Supply minus mixed air, fan off (°C)"),
    "low_coil_capacity": ("chw_valve_cmd_pct_run", "Valve command (%), running"),
}
PLAIN = {NORMAL: "No fault (healthy machine)", **FAULT_NAMES}


@st.cache_resource(show_spinner="Training the model on January to June (about 30 seconds)...")
def load_everything():
    """Data and trained pipeline, loaded once (simulation.load_pipeline)."""
    return load_pipeline()


def hourly(series: pd.Series, timestamps: pd.Series) -> pd.Series:
    """Median per hour, so the charts stay readable."""
    return series.groupby(timestamps.dt.floor("h")).median()


st.set_page_config(page_title="AHU fault simulator", layout="wide")
st.title("AHU fault simulator")
st.write(
    "Pick a machine and a period, inject a fault with the size you want, and see what the "
    "model does: the signal that changes, how sure the model is, and the alarms a technician "
    "would get. You can also change the alarm settings and see how many false alarms appear."
)

try:
    fitted, data, labels = load_everything()
except FileNotFoundError:
    st.error("Data not found. Set AHU_DATA_DIR to the folder with the assignment data files.")
    st.stop()

# Sidebar: the machine and the period
st.sidebar.header("1. Machine and period")
ahu_id = st.sidebar.selectbox("Machine", sorted(data["ahu_id"].unique()), index=1)
first, last = data["timestamp"].min().date(), data["timestamp"].max().date()
window_start = pd.Timestamp(
    st.sidebar.date_input(
        "First day shown", pd.Timestamp("2025-07-07"), min_value=first, max_value=last
    )
)
window_end = window_start + pd.Timedelta(days=WINDOW_DAYS)

# Sidebar: the simulated fault
st.sidebar.header("2. Fault to inject")
fault = st.sidebar.selectbox("Fault", list(PLAIN), format_func=lambda f: PLAIN[f])
fault_start = window_start + pd.Timedelta(days=st.sidebar.slider("Starts on day", 1, 10, 3) - 1)
fault_end = fault_start + pd.Timedelta(days=st.sidebar.slider("Lasts (days)", 1, 7, 4))
size = 0.0
if fault != NORMAL:
    spec = FAULT_SIZES[fault]
    size = st.sidebar.slider(
        spec["label"], float(spec["min"]), float(spec["max"]), float(spec["default"])
    )

# Sidebar: the alarm settings (defaults = the settings of predictions.csv)
st.sidebar.header("3. Alarm settings")
min_prob = st.sidebar.slider("Model confidence needed", 0.5, 0.95, ALARM_MIN_PROB, 0.05)
min_hours = st.sidebar.slider("Minimum alarm (hours running)", 0.5, 6.0, MIN_ALARM_ROWS / 12, 0.5)
gap_hours = st.sidebar.slider("Join alarms closer than (hours)", 0.0, 12.0, MAX_GAP_ROWS / 12, 1.0)

# Simulate: inject the fault into this machine's data and run the whole pipeline (simulation.py)
result = simulate(
    fitted,
    data,
    ahu_id=ahu_id,
    window_start=window_start,
    fault=fault,
    fault_start=fault_start,
    fault_end=fault_end,
    size=size,
    min_prob=min_prob,
    min_alarm_rows=int(min_hours * ROWS_PER_HOUR),
    max_gap_rows=int(gap_hours * ROWS_PER_HOUR),
)
before, after, events = result.before, result.after, result.events
times = after["timestamp"]

# Result in numbers
cols = st.columns(4)
if fault == NORMAL:
    cols[0].metric("Fault injected", "None")
    cols[1].metric("Alarms raised", len(events))
    cols[2].metric("False alarms", result.false_alarms)
else:
    cols[0].metric("Detected", "Yes" if result.detected else "No")
    cols[1].metric("Delay", f"{result.delay_h:.0f} h" if result.detected else "-")
    right = "right" if result.main_type == fault else None
    cols[2].metric("Type", FAULT_NAMES.get(result.main_type, "-"), right)
    cols[3].metric("False alarms", result.false_alarms)
real = labels[
    (labels["ahu_id"] == ahu_id) & (labels["end"] > window_start) & (labels["start"] < window_end)
]
if len(real):
    st.info(
        f"This machine also has a real labelled fault in this window: {real['fault_type'].iloc[0]}"
    )

# Chart 1: the key signal, healthy vs with the fault
col, title = KEY_SIGNAL[fault]
signal = pd.concat(
    {
        "healthy": hourly(before[col], times),
        "with the fault": hourly(after[col], times),
    },
    axis=1,
)
signal = signal.rename_axis("time").reset_index()
signal = signal.melt("time", var_name="data", value_name="value").dropna()
# The same time axis for the three charts, so they line up; the shaded band is the fault
domain = [window_start.isoformat(), window_end.isoformat()]
time_axis = alt.X(
    "time:T", title=None, scale=alt.Scale(domain=domain), axis=alt.Axis(format="%a %d %b")
)
y_axis = alt.Axis(minExtent=45)  # same width for every y axis, so the charts line up
band = pd.DataFrame({"time": [fault_start], "end": [fault_end]})
shade = alt.Chart(band).mark_rect(opacity=0.15, color="#eb6834").encode(x=time_axis, x2="end:T")
lines = (
    alt.Chart(signal)
    .mark_line()
    .encode(
        x=time_axis,
        y=alt.Y("value:Q", title=title, axis=y_axis),
        color=alt.Color(
            "data:N",
            scale=alt.Scale(range=["#9a9893", "#2a78d6"]),
            title=None,
            legend=alt.Legend(orient="bottom"),
        ),
    )
)
st.subheader("1. The signal that shows this fault")
st.altair_chart((shade + lines).properties(height=230), use_container_width=True)

# Chart 2: how sure the model is
prob = hourly(result.fault_probability, times).rename("fault probability")
prob = prob.rename_axis("time").reset_index()
line = (
    alt.Chart(prob)
    .mark_line(color="#8a5cd6")
    .encode(
        x=time_axis,
        y=alt.Y(
            "fault probability:Q",
            title="Fault probability",
            scale=alt.Scale(domain=[0, 1]),
            axis=y_axis,
        ),
    )
)
# Dashed line: the confidence needed for an alarm
limit = alt.Chart(pd.DataFrame({"y": [min_prob]})).mark_rule(strokeDash=[4, 4]).encode(y="y:Q")
st.subheader("2. How sure the model is that something is wrong")
st.altair_chart((shade + line + limit).properties(height=180), use_container_width=True)

# Chart 3: the alarms a technician would get
st.subheader("3. Alarms")
if len(events):
    events["fault"] = events["fault_type"].map(FAULT_NAMES)
    events = events.rename(columns={"start": "time"}).assign(row="Alarms")
    colors = alt.Scale(
        domain=list(FAULT_NAMES.values()), range=[FAULT_COLORS[f] for f in FAULT_NAMES]
    )
    bars = (
        alt.Chart(events)
        .mark_bar(height=18)
        .encode(
            x=time_axis,
            x2="end:T",
            y=alt.Y(
                "row:N", title="Alarms", axis=alt.Axis(labels=False, ticks=False, minExtent=45)
            ),
            color=alt.Color(
                "fault:N", scale=colors, title=None, legend=alt.Legend(orient="bottom")
            ),
        )
    )
    st.altair_chart((shade + bars).properties(height=120), use_container_width=True)
else:
    st.write("No alarm in this window.")

with st.expander("How the faults are simulated"):
    st.markdown(
        "- **Stuck tap** (`chw_valve_stuck`): the real valve stays at the chosen position, so "
        "the coil cools as if it were there; the controller pushes the command to 0% or 100%.\n"
        "- **Stuck flap** (`oa_damper_stuck`): only the chosen share of outdoor air comes in; "
        "mixed air moves to return air, CO2 rises, the damper command goes up.\n"
        "- **Lying thermometer** (`sat_sensor_bias`): the supply sensor reads wrong by the chosen "
        "°C. With the fan on the controller hides it; with the fan off it shows.\n"
        "- **Weak radiator** (`low_coil_capacity`): the coil gives the chosen share of its "
        "cooling; the valve opens more, and when it reaches 100% the air warms.\n\n"
        "Code: `src/ahu_fdd/simulate.py`. The model is the one of `predictions.csv`."
    )
