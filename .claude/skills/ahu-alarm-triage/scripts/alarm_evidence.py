"""Print the evidence for one AHU alarm as JSON, or list the alarms in predictions.csv."""

import argparse
import json
import sys

from ahu_fdd.triage import alarm_evidence, list_alarms, load_ahu


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="list the alarms in predictions.csv")
    parser.add_argument("--ahu", help="machine, for example B1-AHU-11")
    parser.add_argument("--start", help="start of the window, for example 2025-04-23")
    parser.add_argument("--end", help="end of the window, not included")
    args = parser.parse_args()

    if args.list:
        print(list_alarms().to_string(index=False))
        return 0
    if not (args.ahu and args.start and args.end):
        parser.error("use --list, or give --ahu, --start and --end")
    try:
        evidence = alarm_evidence(load_ahu(args.ahu), start=args.start, end=args.end)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
