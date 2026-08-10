"""FastAPI router for the advisory service.

Kept in its own module so that `src.advisory` stays importable without a web
framework: the rules engine and generator must run in CI, in notebooks and in
the SMS worker, none of which need FastAPI.

Endpoints:
    POST /api/v1/advisory          full advisory for one forecast
    POST /api/v1/advisory/sms      the 160-char version only (2G path)
    GET  /api/v1/advisory/health   readiness, including which providers are live

Wire into the app with:

    from src.advisory.api import router as advisory_router
    app.include_router(advisory_router)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .cache import AdvisoryCache
from .generator import generate_advisory, load_llm_config
from .providers import has_credentials
from .rules import load_config
from .schemas import PredictionPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/advisory", tags=["advisory"])

# One process-wide cache. The advisory fires once per season, so hit rates are
# driven by re-delivery (app reopens, SMS resends), not by request volume.
_cache = AdvisoryCache(
    ttl_seconds=load_llm_config()["cache"]["ttl_seconds"],
    max_entries=load_llm_config()["cache"]["max_entries"],
)


class AdvisoryRequest(BaseModel):
    """A forecast from the ML track, plus optional farm context."""

    field_id: str
    crop_type: str
    predicted_yield: float

    date_of_image: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    NDVI: Optional[float] = None
    GNDVI: Optional[float] = None
    SAVI: Optional[float] = None
    soil_moisture: Optional[float] = None
    temperature: Optional[float] = None
    rainfall: Optional[float] = None

    prediction_interval: Optional[List[float]] = None
    model_version: Optional[str] = None
    yield_unit: str = "units/ha"

    area_ha: Optional[float] = None
    farmer_lang: str = "en"
    region: Optional[str] = None

    lang: Optional[str] = Field(
        default=None, description="Override the farmer's stored language"
    )
    use_cache: bool = True


class AdvisoryResponse(BaseModel):
    field_id: str
    lang: str
    headline: str
    body: str
    sms_text: str
    disclaimer: str
    generated_by: str
    llm_model: Optional[str] = None
    verdict: Dict[str, Any]


class SMSResponse(BaseModel):
    field_id: str
    sms_text: str
    characters: int


def _to_payload(request: AdvisoryRequest) -> PredictionPayload:
    data = request.model_dump()
    data.pop("lang", None)
    data.pop("use_cache", None)
    return PredictionPayload.from_dict(data)


@router.post("", response_model=AdvisoryResponse)
async def create_advisory(request: AdvisoryRequest) -> AdvisoryResponse:
    """Generate (or return cached) advisory for one forecast.

    Provider failures do not surface as errors: the generator falls back to the
    rules-only advisory, and `generated_by` records which path was taken.
    """
    try:
        advisory = generate_advisory(
            _to_payload(request),
            lang=request.lang,
            cache=_cache,
            use_cache=request.use_cache,
        )
    except Exception as exc:  # noqa: BLE001 - endpoint must not leak internals
        logger.exception("advisory generation failed for %s", request.field_id)
        raise HTTPException(
            status_code=500, detail="Could not generate advisory"
        ) from exc

    return AdvisoryResponse(
        field_id=advisory.field_id,
        lang=advisory.lang,
        headline=advisory.headline,
        body=advisory.body,
        sms_text=advisory.sms_text,
        disclaimer=advisory.disclaimer,
        generated_by=advisory.generated_by,
        llm_model=advisory.llm_model,
        verdict=advisory.verdict.to_dict(),
    )


@router.post("/sms", response_model=SMSResponse)
async def create_sms_advisory(request: AdvisoryRequest) -> SMSResponse:
    """The 2G path. Rules-rendered, so this never costs an LLM call."""
    from .rules import build_verdict, render_sms

    rules, _ = load_config()
    verdict = build_verdict(_to_payload(request))
    sms = render_sms(verdict, rules)
    return SMSResponse(field_id=verdict.field_id, sms_text=sms, characters=len(sms))


@router.get("/health")
async def health() -> Dict[str, Any]:
    rules, _ = load_config()
    llm_config = load_llm_config()
    providers = [
        {
            "name": p.get("name"),
            "model": p.get("model"),
            "configured": has_credentials(p),
        }
        for p in llm_config.get("providers", [])
    ]
    return {
        "status": "healthy",
        "rules_version": rules["rules_version"],
        "providers": providers,
        # An advisory is still deliverable with zero providers configured.
        "degraded_to_rules_only": not any(p["configured"] for p in providers),
        "cache": _cache.stats(),
    }
