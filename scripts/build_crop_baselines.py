"""Derive per-crop yield baselines and feature percentiles from the training data.

The advisory rules engine compares a predicted yield against a baseline. We have
no multi-year history (the dataset is a single season, Jan-May 2023), so the
baseline is the *within-dataset mean for that crop*. This is a relative signal,
not a district historical average -- see docs/ADVISORY.md for what that means
for the wording of the advisory.

Feature percentiles come from the real Google Earth Engine columns where they
exist (see src/advisory/dataset.py). Thresholds derived from the original
columns would be thresholds on a simulation.

Run:
    python scripts/build_crop_baselines.py
Writes:
    configs/crop_baselines.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.advisory.dataset import FEATURES, load_dataset  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "configs" / "crop_baselines.yaml"
PERCENTILES = [0.10, 0.25, 0.50, 0.75, 0.90]

MIN_ROWS_PER_CROP = 20


def crop_baselines(df: pd.DataFrame) -> dict:
    out = {}
    for crop, grp in df.groupby("crop_type"):
        if len(grp) < MIN_ROWS_PER_CROP:
            continue
        y = grp["yield"]
        out[str(crop)] = {
            "n": int(len(grp)),
            "mean": round(float(y.mean()), 3),
            "std": round(float(y.std()), 3),
            "p10": round(float(y.quantile(0.10)), 3),
            "p90": round(float(y.quantile(0.90)), 3),
        }
    return dict(sorted(out.items()))


def feature_percentiles(df: pd.DataFrame) -> dict:
    """Percentiles per feature, ignoring gaps.

    Real satellite and weather data has holes. Dropping the missing values is
    correct here -- imputing them would invent a distribution, and the rules
    engine already suppresses any rule whose feature is absent on a given row.
    """
    out = {}
    for feat in FEATURES:
        s = df[feat].dropna()
        if s.empty:
            continue
        out[feat] = {
            f"p{int(q * 100)}": round(float(s.quantile(q)), 3) for q in PERCENTILES
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    df, provenance = load_dataset(args.data)
    doc = {
        "_generated_by": "scripts/build_crop_baselines.py",
        "_source": provenance["source_file"],
        "_rows": provenance["rows"],
        "_feature_columns": provenance["feature_columns"],
        "_missing_values": provenance["missing_values"],
        "_caveat": (
            "Single-season (2023-01 to 2023-05) within-dataset baseline. NOT a "
            "multi-year district average. Advisory copy must not claim otherwise."
        ),
        "global_yield": {
            "mean": round(float(df["yield"].mean()), 3),
            "std": round(float(df["yield"].std()), 3),
        },
        "crops": crop_baselines(df),
        "features": feature_percentiles(df),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(doc, fh, sort_keys=False, allow_unicode=True)
    print(f"wrote {args.out} ({len(doc['crops'])} crops, {doc['_rows']} rows)")
    print(f"  source: {provenance['source_file']}")
    for canonical, column in provenance["feature_columns"].items():
        print(f"    {canonical:<14} <- {column}")
    if provenance["missing_values"]:
        print(f"  missing values: {provenance['missing_values']}")


if __name__ == "__main__":
    main()
