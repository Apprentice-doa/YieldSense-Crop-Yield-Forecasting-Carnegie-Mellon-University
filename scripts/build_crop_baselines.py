"""Derive per-crop yield baselines and feature percentiles from the training data.

The advisory rules engine compares a predicted yield against a baseline. We have
no multi-year history (the dataset is a single season, Jan-May 2023), so the
baseline is the *within-dataset mean for that crop*. This is a relative signal,
not a district historical average -- see docs/ADVISORY.md for what that means
for the wording of the advisory.

Run:
    python scripts/build_crop_baselines.py
Writes:
    configs/crop_baselines.yaml
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = REPO_ROOT / "data" / "external" / "yield_prediction_dataset.csv"
DEFAULT_OUT = REPO_ROOT / "configs" / "crop_baselines.yaml"

# NDWI is an exact negation of GNDVI in this dataset (r = -1.0), so it carries no
# information the rules engine can use. Excluded deliberately.
FEATURES = ["NDVI", "GNDVI", "SAVI", "soil_moisture", "temperature", "rainfall"]
PERCENTILES = [0.10, 0.25, 0.50, 0.75, 0.90]

MIN_ROWS_PER_CROP = 20


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    return df


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
    out = {}
    for feat in FEATURES:
        s = df[feat]
        out[feat] = {
            f"p{int(q * 100)}": round(float(s.quantile(q)), 3) for q in PERCENTILES
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    df = load(args.data)
    doc = {
        "_generated_by": "scripts/build_crop_baselines.py",
        "_source": str(args.data.relative_to(REPO_ROOT)).replace("\\", "/"),
        "_rows": int(len(df)),
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


if __name__ == "__main__":
    main()
