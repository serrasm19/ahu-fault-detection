"""Draw the architecture diagram of the report: python report/architecture_diagram.py"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from ahu_fdd.plots import save_fig, set_style

set_style()

# Colours: one per zone, light fill with a darker edge
SITE, CLOUD, TEAM, ML, OPS = "#eb6834", "#2a78d6", "#1baf7a", "#8a5cd6", "#9a9893"


def box(ax, x, y, w, h, title, lines, color):
    """A rounded box with a bold title and a few small lines under it."""
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            facecolor=color + "22",
            edgecolor=color,
            linewidth=1.5,
        )
    )
    ax.text(x + w / 2, y + h - 0.17, title, ha="center", va="top", fontsize=9, weight="bold")
    ax.text(
        x + w / 2,
        y + h - 0.45,
        "\n".join(lines),
        ha="center",
        va="top",
        fontsize=7.2,
        linespacing=1.35,
        color="#333333",
    )


def arrow(ax, start, end, label="", color="#555555", rad=0.0, label_pos=(0, 0.12)):
    """An arrow from start to end, with an optional label near its middle."""
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=12,
            color=color,
            linewidth=1.2,
            connectionstyle=f"arc3,rad={rad}",
        )
    )
    if label:
        mx, my = (start[0] + end[0]) / 2 + label_pos[0], (start[1] + end[1]) / 2 + label_pos[1]
        ax.text(mx, my, label, ha="center", va="bottom", fontsize=7, color=color, style="italic")


fig, ax = plt.subplots(figsize=(13, 7.2))
ax.set_xlim(0, 13)
ax.set_ylim(0, 7.2)
ax.axis("off")

# Three zones: each building, the cloud, the maintenance team
for x, w, label, color in [
    (0.1, 2.6, "Each building (x25)", SITE),
    (3.0, 7.0, "Cloud: Azure + Databricks", CLOUD),
    (10.3, 2.6, "Maintenance team", TEAM),
]:
    ax.add_patch(
        FancyBboxPatch(
            (x, 0.15),
            w,
            6.85,
            boxstyle="round,pad=0.02,rounding_size=0.15",
            facecolor="none",
            edgecolor=color,
            linewidth=1,
            linestyle="--",
        )
    )
    ax.text(x + 0.12, 6.88, label, fontsize=10, weight="bold", color=color, va="top")

# Building: BMS and edge agent
box(
    ax,
    0.35,
    4.9,
    2.1,
    1.4,
    "BMS + SQL Server",
    ["5-minute trend data", "on the Windows edge PC"],
    SITE,
)
box(
    ax,
    0.35,
    2.3,
    2.1,
    1.9,
    "Edge agent",
    [
        "Windows service",
        "reads new rows every 15 min",
        "keeps 7 days if offline",
        "no model on site",
    ],
    SITE,
)

# Cloud, top row: data layers
box(ax, 3.3, 5.2, 2.0, 1.3, "Bronze", ["raw rows as received", "Delta, per building/day"], CLOUD)
box(ax, 5.6, 5.2, 2.0, 1.3, "Silver", ["clean_sensors()", "quality checks"], CLOUD)
box(ax, 7.9, 5.2, 1.9, 1.3, "Gold", ["features", "predictions"], CLOUD)

# Cloud, middle row: training, registry, inference
box(
    ax,
    3.3,
    3.0,
    2.0,
    1.7,
    "Training job",
    ["monthly or new labels", "event-level scorer", "challenger vs champion"],
    ML,
)
box(
    ax,
    5.6,
    3.0,
    2.0,
    1.7,
    "MLflow registry",
    ["model versions + cards", "alias @champion", "2 weeks in shadow"],
    ML,
)
box(ax, 7.9, 3.0, 1.9, 1.7, "Inference job", ["every hour", "per building", "uses @champion"], ML)

# Cloud, bottom row: labels, monitoring, alerts
box(
    ax,
    3.3,
    0.95,
    2.0,
    1.55,
    "Labels",
    ["work orders: confirmed", "or 'no fault found'", "+ faults found in data"],
    ML,
)
box(
    ax,
    5.6,
    0.95,
    2.0,
    1.55,
    "Monitoring",
    ["data freshness, gaps", "alarms per AHU-month", "drift, failed jobs"],
    OPS,
)
box(
    ax,
    7.9,
    0.95,
    1.9,
    1.55,
    "Alert service",
    ["one alarm per fault", "severity by type", "suppress after 'no fault'", "sensor issues apart"],
    CLOUD,
)

# Maintenance team
box(
    ax, 10.55, 4.0, 2.1, 1.8, "CMMS", ["work order via REST API", "evidence: chart + signals"], TEAM
)
box(
    ax,
    10.55,
    1.2,
    2.1,
    2.0,
    "Technician",
    ["checks on site", "closes the order:", "'fault confirmed' or", "'no fault found'"],
    TEAM,
)

# Data flow, from the building to the cloud (outbound only)
arrow(ax, (1.4, 4.9), (1.4, 4.2))
arrow(ax, (2.45, 3.6), (3.3, 5.6), color=SITE)
ax.text(
    2.62,
    4.75,
    "outbound\nHTTPS only",
    fontsize=7,
    color=SITE,
    style="italic",
    ha="center",
    rotation=67,
    va="center",
)
arrow(ax, (5.3, 5.85), (5.6, 5.85))
arrow(ax, (7.6, 5.85), (7.9, 5.85))
arrow(ax, (5.9, 5.2), (5.0, 4.7), "clean history", label_pos=(-0.55, -0.12))
arrow(ax, (8.85, 5.2), (8.85, 4.7), "features", label_pos=(0.45, -0.1))
arrow(ax, (5.3, 3.85), (5.6, 3.85))
arrow(ax, (7.6, 3.85), (7.9, 3.85))
arrow(ax, (8.85, 3.0), (8.85, 2.5), "alarms", label_pos=(0.42, -0.1))
arrow(ax, (9.8, 1.9), (10.55, 4.5), color=TEAM)
arrow(ax, (11.6, 4.0), (11.6, 3.2))

# Feedback loop along the bottom: outcomes become labels for the next training
ax.plot([11.6, 11.6, 4.3], [1.2, 0.5, 0.5], color=ML, linewidth=1.2)
arrow(ax, (4.3, 0.5), (4.3, 0.95), color=ML)
ax.text(7.6, 0.55, "outcomes of the work orders", fontsize=7, color=ML, style="italic", ha="center")
arrow(ax, (4.3, 2.5), (4.3, 3.0), "new labels", color=ML, label_pos=(0.55, -0.1))

ax.set_title("From the BMS to a work order, and back as labels", fontsize=12, pad=8)
save_fig(fig, "architecture")
print("saved")
