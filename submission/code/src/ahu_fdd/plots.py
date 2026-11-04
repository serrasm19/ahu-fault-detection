"""Shared plot style for notebooks and report figures."""

from pathlib import Path

import matplotlib.pyplot as plt

from ahu_fdd.config import CODE_DIR

FIGURES_DIR = CODE_DIR / "figures"

BUILDING_COLORS = {"B1": "#2a78d6", "B2": "#eb6834", "B3": "#1baf7a"}
FAULT_COLORS = {
    "chw_valve_stuck": "#2a78d6",
    "oa_damper_stuck": "#eb6834",
    "sat_sensor_bias": "#1baf7a",
    "low_coil_capacity": "#eda100",
    "normal": "#9a9893",
}
INK = "#52514e"


def set_style() -> None:
    """Apply a light, clean style to all matplotlib figures."""
    plt.rcParams.update(
        {
            "figure.dpi": 110,
            "figure.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "axes.titleweight": "bold",
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": "#e6e5e1",
            "grid.linewidth": 0.6,
            "xtick.color": INK,
            "ytick.color": INK,
            "legend.frameon": False,
            "lines.linewidth": 2,
        }
    )


def save_fig(fig: plt.Figure, name: str, *, folder: Path = FIGURES_DIR) -> Path:
    """Save a figure as PNG for the report and return its path."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return path
