"""Inject one fault at several sizes into healthy AHUs and print how the detector scores."""

import argparse
import sys

import pandas as pd
from ahu_fdd.config import FAULT_TYPES
from ahu_fdd.simulation import load_pipeline, sensitivity_table


def parse_sizes(text: str | None) -> tuple[float, ...] | None:
    """'-1,-2' to (-1.0, -2.0). No text means the default sizes in config.py."""
    return None if text is None else tuple(float(size) for size in text.split(","))


def smallest_found(table: pd.DataFrame) -> str:
    """The first size, in the order tried, from which all clearer sizes are found on this AHU."""
    runs = table.iloc[1:]
    missed = runs.index[~runs["detected"]]
    found = runs.loc[missed.max() + 1 :] if len(missed) else runs
    return "none of the sizes" if found.empty else f"size {found['size'].iloc[0]:g}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ahus", required=True, help="machines, for example B1-AHU-02,B3-AHU-07")
    parser.add_argument("--fault", required=True, choices=FAULT_TYPES)
    parser.add_argument("--start", required=True, help="first day of the 14-day window")
    parser.add_argument("--sizes", help="fault sizes, small to clear, for example 0.5,1,2")
    args = parser.parse_args()

    fitted, data, _ = load_pipeline()
    start = pd.Timestamp(args.start)
    ahus = args.ahus.split(",")
    unknown = set(ahus) - set(data["ahu_id"])
    if unknown:
        print(f"error: unknown machines {sorted(unknown)}", file=sys.stderr)
        return 1

    for ahu_id in ahus:
        table = sensitivity_table(
            fitted,
            data,
            ahu_id=ahu_id,
            fault=args.fault,
            window_start=start,
            sizes=parse_sizes(args.sizes),
        )
        print(table.round(1).to_string(index=False))
        if table.loc[0, "false_alarms"] > 0:
            print(f"WARNING: {ahu_id} has an alarm with no fault. Don't trust this window.")
        print(f"{ahu_id}: found from {smallest_found(table)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
