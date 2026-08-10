"""Input and output contracts for the GenAI Advisory track.

These are plain dataclasses on purpose: the rules engine must be importable and
testable with no web framework and no LLM SDK installed. The FastAPI layer wraps
these with pydantic models at the edge; everything inward of that uses these.

Contract owners:
    PredictionPayload  -- produced by the Data & ML track, consumed by us.
    Advisory           -- produced by us, consumed by Platform/Backend, the SMS
                          renderer, and the Chatbot track (as grounding context).

Field names mirror the training data columns (NDVI, GNDVI, SAVI, soil_moisture,
temperature, rainfall) so there is no translation layer to get wrong. NDWI is
deliberately absent: in this dataset it is an exact negation of GNDVI.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "0.1.0"

URGENCY_ORDER = {"immediate": 0, "soon": 1, "routine": 2}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "none": 3}


@dataclass
class PredictionPayload:
    """One yield forecast for one field, for one season.

    Required fields are what the ML track can produce today. Everything optional
    is enrichment: when it is missing the rules engine degrades gracefully and
    simply emits fewer actions, rather than guessing.
    """

    field_id: str
    crop_type: str
    predicted_yield: float

    # Observation window / location
    date_of_image: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Remote-sensing and weather features
    NDVI: Optional[float] = None
    GNDVI: Optional[float] = None
    SAVI: Optional[float] = None
    soil_moisture: Optional[float] = None
    temperature: Optional[float] = None
    rainfall: Optional[float] = None

    # Model metadata
    prediction_interval: Optional[List[float]] = None  # [lo, hi]
    model_version: Optional[str] = None
    yield_unit: str = "units/ha"

    # Farm context (drives post-harvest quantities; never invented if absent)
    area_ha: Optional[float] = None
    farmer_lang: str = "en"
    region: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PredictionPayload":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Action:
    """One thing the farmer should actually do."""

    rule_id: str
    action: str
    why: str
    urgency: str  # immediate | soon | routine
    severity: str  # high | medium | low | none
    stage: str = "in_season"  # in_season | post_harvest
    # Short form for the 2G path. Without it, half of all SMS messages lose
    # part of the instruction to truncation -- and SMS is the only thing some
    # farmers ever see.
    sms_action: Optional[str] = None

    def sort_key(self) -> tuple:
        return (
            URGENCY_ORDER.get(self.urgency, 9),
            SEVERITY_ORDER.get(self.severity, 9),
            self.rule_id,
        )


@dataclass
class PostHarvestPlan:
    """Resource-allocation guidance. Quantities are None when area_ha is absent."""

    market_note: str
    expected_volume: Optional[float] = None
    volume_unit: Optional[str] = None
    storage_capacity_needed: Optional[float] = None
    drying_days: Optional[int] = None
    labour_days: Optional[float] = None


@dataclass
class Verdict:
    """The deterministic output of the rules engine.

    This is the single source of truth for every number the farmer sees. The LLM
    receives this object and may only rephrase and translate it -- see
    src/advisory/prompts/system.md.
    """

    field_id: str
    crop_type: str
    predicted_yield: float
    yield_unit: str
    baseline_yield: Optional[float]
    baseline_ratio: Optional[float]
    band: str  # critical | below | on_track | above | unknown
    band_label: str
    confidence: str  # high | medium | low | unknown
    prediction_interval: Optional[List[float]]
    drivers: List[str] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    post_harvest: Optional[PostHarvestPlan] = None
    suppressed_rules: List[str] = field(default_factory=list)
    data_quality_flags: List[str] = field(default_factory=list)
    rules_version: str = ""
    schema_version: str = SCHEMA_VERSION
    baseline_caveat: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def numeric_facts(self) -> List[float]:
        """Every number the LLM is allowed to state.

        The eval harness asserts that no number in the generated prose is absent
        from this list -- this is the numeric-fidelity check that stops the model
        inventing yield figures.
        """
        vals: List[float] = [self.predicted_yield]
        for v in (self.baseline_yield, self.baseline_ratio):
            if v is not None:
                vals.append(v)
        if self.prediction_interval:
            vals.extend(self.prediction_interval)
        ph = self.post_harvest
        if ph is not None:
            for v in (
                ph.expected_volume,
                ph.storage_capacity_needed,
                ph.drying_days,
                ph.labour_days,
            ):
                if v is not None:
                    vals.append(float(v))
        return vals


@dataclass
class Advisory:
    """The farmer-facing artefact. `sms_text` is rules-rendered, not LLM-written."""

    field_id: str
    lang: str
    headline: str
    body: str
    sms_text: str
    verdict: Verdict
    disclaimer: str
    generated_by: str = "rules"  # rules | llm | llm_fallback_rules
    llm_model: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
