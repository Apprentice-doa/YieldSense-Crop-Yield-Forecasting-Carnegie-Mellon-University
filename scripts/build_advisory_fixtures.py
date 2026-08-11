"""Build advisory test fixtures from real rows of the training data.

We want fixtures that exercise every yield band and every data-quality path, but
we do not want invented feature values -- hand-typed NDVI/rainfall combinations
drift away from what the model will actually see. So: pick real rows that land
in each band, then add a small number of explicitly synthetic edge cases that
the real data does not contain (missing fields, no area, cloud-corrupted NDVI).

Run:
    python scripts/build_advisory_fixtures.py
Writes:
    tests/fixtures/advisory/*.json
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data" / "external" / "yield_prediction_dataset.csv"
BASELINES = REPO_ROOT / "configs" / "crop_baselines.yaml"
OUT_DIR = REPO_ROOT / "tests" / "fixtures" / "advisory"

FEATURES = ["NDVI", "GNDVI", "SAVI", "soil_moisture", "temperature", "rainfall"]


def row_to_payload(row: pd.Series, **overrides) -> dict:
    payload = {
        "field_id": str(row["field_id"]),
        "crop_type": str(row["crop_type"]),
        "predicted_yield": round(float(row["yield"]), 3),
        "date_of_image": str(row["date_of_image"]),
        "latitude": round(float(row["latitude"]), 6),
        "longitude": round(float(row["longitude"]), 6),
        **{f: round(float(row[f]), 4) for f in FEATURES},
        "prediction_interval": [
            round(float(row["yield"]) * 0.92, 3),
            round(float(row["yield"]) * 1.08, 3),
        ],
        "model_version": "fixture-v0",
        "yield_unit": "units/ha",
        "area_ha": 1.5,
        "farmer_lang": "en",
    }
    payload.update(overrides)
    return payload


def pick_band_rows(df: pd.DataFrame, baselines: dict) -> dict:
    """One real row per band, chosen by ratio to the crop baseline."""
    means = {c: v["mean"] for c, v in baselines["crops"].items()}
    df = df[df["crop_type"].isin(means)].copy()
    df["ratio"] = df.apply(lambda r: r["yield"] / means[r["crop_type"]], axis=1)

    picks = {}
    bands = {
        "critical": df[df["ratio"] < 0.70],
        "below": df[(df["ratio"] >= 0.70) & (df["ratio"] < 0.90)],
        "on_track": df[(df["ratio"] >= 0.90) & (df["ratio"] < 1.10)],
        "above": df[df["ratio"] >= 1.10],
    }
    for band, subset in bands.items():
        if subset.empty:
            print(f"  !! no real row lands in band '{band}' -- fixture skipped")
            continue
        # Middle of each band, sorted for determinism (no random seed to drift).
        subset = subset.sort_values(["ratio", "field_id", "date_of_image"])
        picks[band] = subset.iloc[len(subset) // 2]
    return picks


def main() -> None:
    df = pd.read_csv(DATA)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    with BASELINES.open(encoding="utf-8") as fh:
        baselines = yaml.safe_load(fh)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = []

    # --- real rows, one per band ---
    for band, row in pick_band_rows(df, baselines).items():
        payload = row_to_payload(row)
        path = OUT_DIR / f"band_{band}.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        written.append((path.name, f"real row, {row['crop_type']}"))

    # --- synthetic edge cases the real data does not contain ---
    base_row = df.sort_values(["field_id", "date_of_image"]).iloc[0]

    edges = {
        # Cloud/water contaminated scene: NDVI below zero is not a crop signal.
        "edge_invalid_ndvi.json": row_to_payload(base_row, NDVI=-1.0, GNDVI=-1.0),
        # Subsistence plot with no recorded area -> no post-harvest quantities.
        "edge_no_area.json": row_to_payload(base_row, area_ha=None),
        # Model is very unsure -> hedged wording, low confidence.
        "edge_wide_interval.json": row_to_payload(
            base_row,
            prediction_interval=[
                round(float(base_row["yield"]) * 0.5, 3),
                round(float(base_row["yield"]) * 1.5, 3),
            ],
        ),
        # Crop we have no baseline for -> band must degrade to "unknown".
        "edge_unknown_crop.json": row_to_payload(base_row, crop_type="Teff"),
        # Weather feed dropped out mid-season.
        "edge_missing_weather.json": row_to_payload(
            base_row, rainfall=None, temperature=None, soil_moisture=None
        ),
        # Heat stress: above the absolute 35C threshold, not a percentile.
        "edge_heat_stress.json": row_to_payload(base_row, temperature=41.2),
    }
    for name, payload in edges.items():
        (OUT_DIR / name).write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        written.append((name, "synthetic edge case"))

    print(f"wrote {len(written)} fixtures to {OUT_DIR.relative_to(REPO_ROOT)}")
    for name, note in written:
        print(f"  {name:32s} {note}")


if __name__ == "__main__":
    main()
