"""Paths and settings for the whole project."""

import os
from dataclasses import dataclass
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = CODE_DIR.parents[1] / "assignment" / "data"

# The four fault labels used by the client, and the plain names I use in notebooks and docs
FAULT_TYPES = ("chw_valve_stuck", "oa_damper_stuck", "sat_sensor_bias", "low_coil_capacity")
FAULT_NAMES = {
    "chw_valve_stuck": "stuck tap",
    "oa_damper_stuck": "stuck flap",
    "sat_sensor_bias": "lying thermometer",
    "low_coil_capacity": "weak radiator",
}
NORMAL = "normal"

# The BMS logs one row per AHU every 5 minutes
SAMPLING = "5min"
SEED = 42

# One office week (B1) was saved in UTC instead of local time (UTC+8), so its stamps are
# 8 hours early. These are the wrong stamps: real local time is 2 June 00:00 to 9 June 00:00.
CLOCK_SHIFT_BUILDING = "B1"
CLOCK_SHIFT_START = "2025-06-01 16:00"
CLOCK_SHIFT_END = "2025-06-08 16:00"
CLOCK_SHIFT_OFFSET = "8h"

# One mall machine logged fan power in watts instead of kW for three weeks (end not included)
POWER_IN_WATTS_AHU = "B3-AHU-04"
POWER_IN_WATTS_START = "2025-04-01"
POWER_IN_WATTS_END = "2025-04-22"

# The CO2 sensors read from 0 to 5000 ppm. Exactly 0 or 5000 means a glitch, not a real value
CO2_LIMITS = (0, 5000)

# A temperature sensor that doesn't change at all for this long is frozen (normal max: ~1.5 h)
FROZEN_SENSORS = ("sat_c", "mat_c", "rat_c", "oat_c", "chwst_c")
FROZEN_MIN_HOURS = 6

# Physics features: below these limits the formulas divide by almost zero
MIN_MIX_DELTA_C = 2.0  # outdoor minus return air, for the outdoor air fraction
MIN_VALVE_PCT = 20.0  # valve opening, for cooling per valve
MIN_REST_MINUTES = 60  # fan off for at least this long before comparing supply and mixed air

# Model features: the machine must run for this long before its readings count (notebook 03),
# windows to smooth the readings (in 5-minute rows), and how long the last check at rest is kept
STARTUP_MINUTES = 30
SHORT_WINDOW_ROWS = 12  # 1 hour
LONG_WINDOW_ROWS = 36  # 3 hours
REST_CHECK_KEEP_ROWS = 576  # 48 hours
LOAD_BIN = (
    1.0  # cooling work (fan speed share x °C cooled) grouped in steps of 1 for the valve curve
)

# Rules baseline: one simple physics rule per fault (notebook 04), on the smoothed signals
RULES = {
    "tap_error_c": 2.5,  # supply air off target vs the AHU normal, °C
    "tap_at_limit": 0.5,  # share of the last hour with the valve command at 0% or 100%
    "flap_fraction_drop": 0.05,  # outdoor air fraction below the AHU normal by this much
    "flap_fraction_max": 0.03,  # and almost no outdoor air
    "bias_offset_c": 1.5,  # check at rest away from the AHU normal, °C
    "weak_valve_excess": 10.0,  # valve more open than this machine needs for the same work, points
}

# Post-processing: an alarm must last at least this many fan-on rows (2 hours)
MIN_ALARM_ROWS = 24

# Faults I found in the data with no work order (notebook 04). Added to the labels for training
EXTRA_LABELS = (
    {
        "ahu_id": "B1-AHU-11",
        "fault_type": "oa_damper_stuck",
        "start": "2025-04-22 07:00",
        "end": "2025-04-30 16:00",
    },
)

# Validation: three blocks of about two months. The cuts fall on days with no labelled event
# in progress, so no event is split between training and validation
FOLDS = (
    ("2025-01-01", "2025-03-02"),
    ("2025-03-02", "2025-04-26"),
    ("2025-04-26", "2025-07-01"),
)


@dataclass(frozen=True)
class Paths:
    """Where the data is read from and where outputs are written."""

    # AHU_DATA_DIR lets you point to the data folder of the assignment package
    data_dir: Path = Path(os.environ.get("AHU_DATA_DIR", DEFAULT_DATA_DIR))
    output_dir: Path = CODE_DIR.parent

    @property
    def train(self) -> Path:
        return self.data_dir / "ahu_train.parquet"

    @property
    def test(self) -> Path:
        return self.data_dir / "ahu_test.parquet"

    @property
    def labels(self) -> Path:
        return self.data_dir / "fault_labels_train.csv"

    @property
    def metadata(self) -> Path:
        return self.data_dir / "ahu_metadata.csv"

    @property
    def predictions(self) -> Path:
        return self.output_dir / "predictions.csv"


PATHS = Paths()
