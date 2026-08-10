"""Generate the end-of-season performance report.

Compares what we forecast against what was actually harvested. The proposal
promises farmers can generate performance reports; this is the command that
produces one.

    python scripts/season_report.py --demo          # simulated harvest results
    python scripts/season_report.py --input results.json
    python scripts/season_report.py --input results.json --json out.json

`results.json` is a list of prediction payloads, each with an `actual_yield`
added once the harvest is in. Records without one are skipped -- a missing
harvest figure is not a zero.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.advisory.report import build_season_report  # noqa: E402

GOLDEN = REPO_ROOT / "tests" / "fixtures" / "golden" / "golden_set.json"


def demo_records() -> List[Dict[str, Any]]:
    """Golden-set forecasts with plausible harvest outcomes attached.

    The ML track has not produced real forecasts yet, and no season has closed,
    so there are no true outcomes to report on. These are clearly simulated --
    the point is to exercise and show the report, not to claim accuracy we have
    not measured. Deterministic, so the demo reads the same every time.
    """
    doc = json.loads(GOLDEN.read_text(encoding="utf-8"))
    records = []
    # Fixed multipliers rather than random: a demo that changes each run is
    # impossible to talk over, and randomness is banned from reproducible output.
    drifts = [1.02, 0.88, 1.15, 0.97, 1.31, 0.72, 1.05, 0.94, 1.09, 0.99]
    for i, item in enumerate(doc["items"][:10]):
        payload = dict(item["payload"])
        payload["actual_yield"] = round(
            payload["predicted_yield"] * drifts[i % len(drifts)], 2
        )
        records.append(payload)
    return records


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=None)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--season", default="2023 Jan-May")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    if args.demo:
        records = demo_records()
        print("NOTE: simulated harvest outcomes. No season has closed yet.\n")
    elif args.input:
        records = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        ap.error("pass --input results.json or --demo")

    report = build_season_report(records, season=args.season)
    print(report.to_text())

    if args.json:
        args.json.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
