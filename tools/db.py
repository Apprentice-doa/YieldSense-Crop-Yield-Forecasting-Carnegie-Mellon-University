from __future__ import annotations
from collections import defaultdict
from typing import Any
from sqlalchemy.orm import Session
from src.db.models.yield_record import YieldRecord

def get_yield_history(db: Session, farmer_id: int) -> list[dict]:
    """Return all yield records for a farmer, ordered by season."""
    records = (
        db.query(YieldRecord)
        .filter(YieldRecord.farmer_id == farmer_id)
        .order_by(YieldRecord.created_at)
        .all()
    )
    return [
        {
            "season": r.season,
            "crop_type": r.crop_type,
            "predicted_yield_kg_per_ha": r.predicted_yield_kg_per_ha,
            "actual_yield_kg_per_ha": r.actual_yield_kg_per_ha,
            "planting_date": str(r.planting_date) if r.planting_date else None,
            "harvest_date": str(r.harvest_date) if r.harvest_date else None,
        }
        for r in records
    ]

def get_yield_summary(db: Session, farmer_id: int) -> dict:
    """Aggregate yield stats per crop across all seasons."""
    records = get_yield_history(db, farmer_id)
    if not records:
        return {}

    by_crop: dict[str, list[float]] = defaultdict(list)
    for r in records:
        val = r["actual_yield_kg_per_ha"] or r["predicted_yield_kg_per_ha"]
        by_crop[r["crop_type"]].append(val)

    return {
        crop: {
            "seasons": len(vals),
            "avg_yield_kg_per_ha": round(sum(vals) / len(vals), 2),
            "max_yield_kg_per_ha": max(vals),
            "min_yield_kg_per_ha": min(vals),
        }
        for crop, vals in by_crop.items()
    }

def build_yield_chart(db: Session, farmer_id: int) -> dict[str, Any] | None:
    """Return a Plotly JSON bar chart of predicted vs actual yield per season."""
    records = get_yield_history(db, farmer_id)
    if not records:
        return None

    seasons = [r["season"] for r in records]
    predicted = [r["predicted_yield_kg_per_ha"] for r in records]
    actual = [r["actual_yield_kg_per_ha"] for r in records]

    return {
        "data": [
            {"type": "bar", "name": "Predicted", "x": seasons, "y": predicted},
            {"type": "bar", "name": "Actual", "x": seasons, "y": actual},
        ],
        "layout": {
            "title": "Yield History — Predicted vs Actual (kg/ha)",
            "barmode": "group",
            "xaxis": {"title": "Season"},
            "yaxis": {"title": "Yield (kg/ha)"},
        },
    }
