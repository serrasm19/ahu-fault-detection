import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from ahu_fdd.config import FAULT_TYPES  # noqa: E402
from ahu_fdd.plots import FAULT_COLORS, save_fig, set_style  # noqa: E402


def test_every_fault_type_has_a_color():
    assert set(FAULT_TYPES) | {"normal"} == set(FAULT_COLORS)


def test_save_fig_writes_png(tmp_path):
    set_style()
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    path = save_fig(fig, "test", folder=tmp_path)
    plt.close(fig)
    assert path.exists() and path.suffix == ".png"
