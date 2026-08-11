"""Build the D5-D6 golden set: 32 forecasts the advisory must handle well.

Stratified, not random. The coverage run showed the `critical` band is 1.0% of
real rows -- uniform sampling would put roughly zero of our worst-news cases in
a 30-item set, and that is exactly the copy we most need reviewed. So each band
gets equal weight, crops are spread across strata, and the data-quality and
low-confidence paths are represented explicitly.

Prediction intervals are synthetic: the ML track does not yet emit them. Each
item records `interval_is_synthetic` so nobody reads a confidence metric off
this set and mistakes it for measured.

Run:
    python scripts/build_advisory_golden_set.py
Writes:
    tests/fixtures/golden/golden_set.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

DATA = REPO_ROOT / "data" / "external" / "yield_prediction_dataset.csv"
BASELINES = REPO_ROOT / "configs" / "crop_baselines.yaml"
OUT = REPO_ROOT / "tests" / "fixtures" / "golden" / "golden_set.json"

FEATURES = ["NDVI", "GNDVI", "SAVI", "soil_moisture", "temperature", "rainfall"]
PER_BAND = 6
ASSUMED_AREA_HA = 1.5
INTERVAL_WIDTH = 0.08


def to_payload(row: pd.Series, **overrides) -> Dict[str, Any]:
    y = float(row["yield"])
    payload = {
        "field_id": str(row["field_id"]),
        "crop_type": str(row["crop_type"]),
        "predicted_yield": round(y, 3),
        "date_of_image": str(row["date_of_image"]),
        "latitude": round(float(row["latitude"]), 6),
        "longitude": round(float(row["longitude"]), 6),
        **{f: round(float(row[f]), 4) for f in FEATURES},
        "prediction_interval": [
            round(y * (1 - INTERVAL_WIDTH), 3),
            round(y * (1 + INTERVAL_WIDTH), 3),
        ],
        "model_version": "golden-v0",
        "yield_unit": "units/ha",
        "area_ha": ASSUMED_AREA_HA,
        "farmer_lang": "en",
    }
    payload.update(overrides)
    return payload


def spread_across_crops(subset: pd.DataFrame, n: int) -> List[pd.Series]:
    """Take up to n rows, preferring one per crop before repeating a crop."""
    subset = subset.sort_values(["ratio", "field_id", "date_of_image"])
    picked: List[pd.Series] = []
    seen_crops = set()

    for _, row in subset.iterrows():
        if len(picked) >= n:
            break
        if row["crop_type"] in seen_crops:
            continue
        seen_crops.add(row["crop_type"])
        picked.append(row)

    for _, row in subset.iterrows():  # top up if crops ran out
        if len(picked) >= n:
            break
        if not any(r.equals(row) for r in picked):
            picked.append(row)
    return picked


def main() -> None:
    df = pd.read_csv(DATA)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    with BASELINES.open(encoding="utf-8") as fh:
        baselines = yaml.safe_load(fh)

    means = {c: v["mean"] for c, v in baselines["crops"].items()}
    df = df[df["crop_type"].isin(means)].copy()
    df["ratio"] = df.apply(lambda r: r["yield"] / means[r["crop_type"]], axis=1)

    bands = {
        "critical": df[df["ratio"] < 0.70],
        "below": df[(df["ratio"] >= 0.70) & (df["ratio"] < 0.90)],
        "on_track": df[(df["ratio"] >= 0.90) & (df["ratio"] < 1.10)],
        "above": df[df["ratio"] >= 1.10],
    }

    items: List[Dict[str, Any]] = []
    for band, subset in bands.items():
        available = len(subset)
        for i, row in enumerate(spread_across_crops(subset, PER_BAND)):
            items.append(
                {
                    "id": f"{band}_{i + 1}",
                    "stratum": band,
                    "why_included": f"{band} band, {row['crop_type']}",
                    "interval_is_synthetic": True,
                    "payload": to_payload(row),
                }
            )
        if available < PER_BAND:
            print(
                f"  !! band '{band}' has only {available} real rows; "
                f"took {min(available, PER_BAND)}"
            )

    # Paths that matter but are rare or absent in the data.
    base = df.sort_values(["field_id", "date_of_image"]).iloc[0]
    specials = [
        (
            "dq_invalid_ndvi",
            "cloud/water contaminated scene -- vegetation rules must be suppressed",
            to_payload(base, NDVI=-1.0, GNDVI=-1.0),
        ),
        (
            "dq_missing_weather",
            "weather feed dropped -- weather rules must be suppressed",
            to_payload(base, rainfall=None, temperature=None, soil_moisture=None),
        ),
        (
            "no_area",
            "subsistence plot with no recorded area -- no invented quantities",
            to_payload(base, area_ha=None),
        ),
        (
            "low_confidence",
            "wide interval -- advisory must hedge",
            to_payload(
                base,
                prediction_interval=[
                    round(float(base["yield"]) * 0.5, 3),
                    round(float(base["yield"]) * 1.5, 3),
                ],
            ),
        ),
        (
            "unknown_crop",
            "crop with no baseline -- must degrade, not guess",
            to_payload(base, crop_type="Teff"),
        ),
        (
            "heat_stress",
            "absolute-threshold rule, rare in this dataset",
            to_payload(base, temperature=41.2),
        ),
        (
            "cold_stress",
            "absolute-threshold rule the stratified sample never hits",
            to_payload(base, temperature=2.5),
        ),
        (
            "water_conflict",
            "dry catchment + wet field -- conflict resolution must fire",
            to_payload(base, rainfall=1.0, soil_moisture=60.0),
        ),
    ]
    for item_id, why, payload in specials:
        items.append(
            {
                "id": item_id,
                "stratum": "edge",
                "why_included": why,
                "interval_is_synthetic": True,
                "payload": payload,
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "_generated_by": "scripts/build_advisory_golden_set.py",
                "_caveat": (
                    "Predicted yields are the dataset's recorded yields, used as "
                    "stand-in forecasts: the advisory is what is under test, not "
                    "the model. Prediction intervals and area_ha are synthetic."
                ),
                "count": len(items),
                "items": items,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    by_stratum: Dict[str, int] = {}
    for item in items:
        by_stratum[item["stratum"]] = by_stratum.get(item["stratum"], 0) + 1
    print(f"wrote {len(items)} items to {OUT.relative_to(REPO_ROOT)}")
    for stratum, n in by_stratum.items():
        print(f"  {stratum:12s} {n}")


if __name__ == "__main__":
    main()
