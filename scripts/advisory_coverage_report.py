"""Run the advisory rules engine across the whole dataset and report behaviour.

This is D5-D6 work that does not need the ML model. The advisory consumes a
predicted yield; whether that number came from a trained model or from the
dataset's recorded yield does not change whether the resulting advisory is
well-formed, grounded, safe and non-contradictory. So we use every real row as
a stand-in forecast and look at what the rules actually do at scale.

What it surfaces:
  - dead rules (never fire on real data -> the threshold is wrong or the rule is
    untestable, and either way it is not earning its place)
  - over-firing rules (fire on nearly everything -> the advice is noise)
  - band distribution (is "critical" so rare the copy is never exercised?)
  - conflict frequency, suppression rates, SMS truncation, action counts

Run:
    python scripts/advisory_coverage_report.py
    python scripts/advisory_coverage_report.py --json out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import List

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.advisory.rules import (  # noqa: E402
    build_verdict,
    load_config,
    render_rules_advisory,
)
from src.advisory.schemas import PredictionPayload  # noqa: E402

DATA = REPO_ROOT / "data" / "external" / "yield_prediction_dataset.csv"
FEATURES = ["NDVI", "GNDVI", "SAVI", "soil_moisture", "temperature", "rainfall"]

# The dataset has no prediction intervals. We synthesise a plausible one so the
# confidence path is exercised; flagged in the output so nobody mistakes it for
# a measured quantity.
SYNTHETIC_INTERVAL_WIDTH = 0.08
ASSUMED_AREA_HA = 1.5


def row_to_payload(row: pd.Series) -> PredictionPayload:
    y = float(row["yield"])
    return PredictionPayload(
        field_id=str(row["field_id"]),
        crop_type=str(row["crop_type"]),
        predicted_yield=y,
        date_of_image=str(row["date_of_image"]),
        latitude=float(row["latitude"]),
        longitude=float(row["longitude"]),
        prediction_interval=[
            round(y * (1 - SYNTHETIC_INTERVAL_WIDTH), 3),
            round(y * (1 + SYNTHETIC_INTERVAL_WIDTH), 3),
        ],
        area_ha=ASSUMED_AREA_HA,
        yield_unit="units/ha",
        **{f: float(row[f]) for f in FEATURES},
    )


def pct(n: int, total: int) -> str:
    return f"{100 * n / total:5.1f}%" if total else "  n/a"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--json", type=Path, default=None, help="also write raw counts")
    args = ap.parse_args()

    df = pd.read_csv(args.data)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    rules, _ = load_config()
    config = load_config()
    all_rule_ids = [r["id"] for r in rules["drivers"]]

    bands: Counter = Counter()
    confidence: Counter = Counter()
    fired: Counter = Counter()
    suppressed: Counter = Counter()
    dq_flags: Counter = Counter()
    action_counts: Counter = Counter()
    sms_lengths: List[int] = []
    sms_truncated = 0
    conflicts_hit = 0
    unknown_crop = 0
    no_in_season_action = 0

    conflict_ids = {
        frozenset(c["when_all"]): c["id"] for c in rules.get("conflicts", [])
    }

    total = len(df)
    for _, row in df.iterrows():
        payload = row_to_payload(row)
        verdict = build_verdict(payload, config)
        advisory = render_rules_advisory(verdict, rules)

        bands[verdict.band] += 1
        confidence[verdict.confidence] += 1
        if verdict.band == "unknown":
            unknown_crop += 1

        in_season = [a for a in verdict.actions if a.stage == "in_season"]
        action_counts[len(in_season)] += 1
        if not in_season:
            no_in_season_action += 1

        for action in verdict.actions:
            fired[action.rule_id] += 1
        for rule_id in verdict.suppressed_rules:
            suppressed[rule_id] += 1
        for flag in verdict.data_quality_flags:
            dq_flags[flag] += 1

        # A conflict fired if both members were suppressed-or-kept together.
        for group in conflict_ids:
            if group & set(verdict.suppressed_rules) and group - set(
                verdict.suppressed_rules
            ):
                conflicts_hit += 1
                break

        sms_lengths.append(len(advisory.sms_text))
        # True truncation: the authored instruction did not survive intact.
        in_season = [a for a in verdict.actions if a.stage == "in_season"]
        top = (
            in_season[0]
            if in_season
            else (verdict.actions[0] if verdict.actions else None)
        )
        if top is not None and (top.sms_action or top.action) not in advisory.sms_text:
            sms_truncated += 1

    print(f"\nAdvisory coverage over {total} rows  ({args.data.name})")
    print("=" * 66)
    print("NOTE: prediction intervals and area_ha are synthetic placeholders.")
    print("      Bands and driver rules use real feature values.\n")

    print("Yield bands")
    for band in ("critical", "below", "on_track", "above", "unknown"):
        n = bands.get(band, 0)
        print(f"  {band:12s} {n:5d}  {pct(n, total)}")

    print("\nConfidence")
    for level, n in confidence.most_common():
        print(f"  {level:12s} {n:5d}  {pct(n, total)}")

    print("\nDriver rules -- fire rate")
    for rule_id in all_rule_ids:
        n = fired.get(rule_id, 0)
        marker = ""
        if n == 0:
            marker = "  <-- NEVER FIRES"
        elif n / total > 0.60:
            marker = "  <-- fires on most rows"
        print(f"  {rule_id:20s} {n:5d}  {pct(n, total)}{marker}")

    print("\nSuppressed (data quality or conflict)")
    if suppressed:
        for rule_id, n in suppressed.most_common():
            print(f"  {rule_id:20s} {n:5d}  {pct(n, total)}")
    else:
        print("  none")

    print("\nData-quality flags")
    if dq_flags:
        for flag, n in dq_flags.most_common(10):
            print(f"  {flag:20s} {n:5d}  {pct(n, total)}")
    else:
        print("  none")

    print("\nIn-season actions per advisory")
    for count in sorted(action_counts):
        n = action_counts[count]
        print(f"  {count} action(s)   {n:5d}  {pct(n, total)}")
    print(
        f"  advisories with no in-season action: {no_in_season_action} "
        f"({pct(no_in_season_action, total).strip()})"
    )

    print("\nSMS")
    print(f"  max length      {max(sms_lengths)}")
    print(f"  mean length     {sum(sms_lengths) / len(sms_lengths):.1f}")
    print(f"  instruction cut {sms_truncated}  {pct(sms_truncated, total)}")

    print(f"\nConflicts resolved: {conflicts_hit}  {pct(conflicts_hit, total)}")
    print(f"Unknown crop:       {unknown_crop}  {pct(unknown_crop, total)}\n")

    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "rows": total,
                    "bands": dict(bands),
                    "confidence": dict(confidence),
                    "fired": dict(fired),
                    "suppressed": dict(suppressed),
                    "data_quality_flags": dict(dq_flags),
                    "action_counts": {str(k): v for k, v in action_counts.items()},
                    "sms_max": max(sms_lengths),
                    "conflicts_resolved": conflicts_hit,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
