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
