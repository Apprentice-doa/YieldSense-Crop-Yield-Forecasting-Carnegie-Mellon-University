"""Turning a dataset row into a PredictionPayload.

The dataset now carries two parallel sets of indices:

- the original columns (`NDVI`, `rainfall`, `temperature`, ...)
- Google Earth Engine computations (`gee_ndvi`, `gee_rainfall`, `gee_temp`, ...)

**We prefer the GEE columns.** They are real measurements of the field, and the
driver rules exist to describe real conditions -- whether to irrigate, whether to
walk the field -- not to predict the yield number.

That distinction matters, because on this dataset the two disagree sharply:

    correlation with `yield`     original      GEE
    rainfall                        0.756     0.162
    NDVI                            0.340     0.063
    SAVI                            0.340     0.074

The original columns predict `yield` almost perfectly and the real satellite
data barely does. The most economical explanation is that `yield` was generated
*from* the original columns, which makes their predictive power an artefact
rather than a finding. Advice grounded in them would be advice grounded in a
simulation. See docs/ADVISORY.md.

Real data also arrives incomplete -- `gee_temp` is missing for 95 rows and
`gee_rainfall` for 26. That is handled, not patched over: a missing feature is
left as None, and the rules engine suppresses any rule that depends on it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]

# Preferred source first. The canonical name is what PredictionPayload uses, so
# the API contract does not change when the underlying columns do.
COLUMN_PREFERENCE: Dict[str, List[str]] = {
    "NDVI": ["gee_ndvi", "NDVI"],
    "GNDVI": ["gee_gndvi", "GNDVI"],
    "SAVI": ["gee_savi", "SAVI"],
    "rainfall": ["gee_rainfall", "rainfall"],
    "temperature": ["gee_temp", "temperature"],
    # No GEE equivalent was computed; the original column is all we have.
    "soil_moisture": ["soil_moisture"],
}

# NDWI is excluded deliberately: it is an exact negation of GNDVI in both the
# original and the GEE columns, so it carries no information the rules can use.

FEATURES = list(COLUMN_PREFERENCE)

DATASETS = [
    REPO_ROOT / "data" / "raw" / "crop_prediction_gee_computations.csv",
    REPO_ROOT / "data" / "external" / "yield_prediction_dataset.csv",
]


def default_dataset() -> Path:
    """The newest dataset present, preferring the GEE computations."""
    for path in DATASETS:
        if path.exists():
            return path
    raise FileNotFoundError(f"no dataset found; looked in {[str(p) for p in DATASETS]}")


def resolve_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Map each canonical feature to the best column actually present."""
    resolved: Dict[str, Optional[str]] = {}
    for canonical, candidates in COLUMN_PREFERENCE.items():
        resolved[canonical] = next((c for c in candidates if c in df.columns), None)
    return resolved


def load_dataset(path: Optional[Path] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Load a dataset and normalise it to the canonical feature names.

    Returns (dataframe, provenance). The provenance records which real column
    fed each canonical feature, so a config generated from it can say where its
    numbers came from instead of leaving the reader to guess.
    """
    path = path or default_dataset()
    raw = pd.read_csv(path)
    raw = raw.loc[:, ~raw.columns.str.startswith("Unnamed")]

    resolved = resolve_columns(raw)
    df = pd.DataFrame(
        {
            "field_id": raw["field_id"].astype(str),
            "crop_type": raw["crop_type"].astype(str),
            "date_of_image": raw["date_of_image"].astype(str),
            "yield": raw["yield"].astype(float),
        }
    )
    for canonical, column in resolved.items():
        df[canonical] = pd.to_numeric(raw[column], errors="coerce") if column else pd.NA

    # Optional and now absent from the GEE export; kept when a dataset has them.
    for optional in ("latitude", "longitude"):
        if optional in raw.columns:
            df[optional] = pd.to_numeric(raw[optional], errors="coerce")

    provenance = {
        "source_file": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "rows": int(len(df)),
        "feature_columns": {k: (v or "MISSING") for k, v in resolved.items()},
        "using_gee": any((v or "").startswith("gee_") for v in resolved.values()),
        "missing_values": {
            feature: int(df[feature].isna().sum())
            for feature in FEATURES
            if df[feature].isna().any()
        },
    }
    return df, provenance


def row_to_payload_dict(row: pd.Series, **overrides: Any) -> Dict[str, Any]:
    """One canonical row -> a PredictionPayload dict.

    NaN becomes None rather than a number, so the rules engine sees a missing
    feature and suppresses the rules that depend on it.
    """
    payload: Dict[str, Any] = {
        "field_id": str(row["field_id"]),
        "crop_type": str(row["crop_type"]),
        "date_of_image": str(row["date_of_image"]),
        "predicted_yield": round(float(row["yield"]), 3),
        "yield_unit": "units/ha",
    }
    for feature in FEATURES:
        value = row.get(feature)
        payload[feature] = None if pd.isna(value) else round(float(value), 4)

    for optional in ("latitude", "longitude"):
        if optional in row and not pd.isna(row[optional]):
            payload[optional] = round(float(row[optional]), 6)

    payload.update(overrides)
    return payload
