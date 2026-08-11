"""On-prediction-complete trigger.

The advisory is a push product: the farmer does not ask for it. When the ML
track finishes a seasonal forecast it calls `on_prediction_complete()`, and the
advisory is generated and handed to whatever sinks are registered (database,
SMS queue, notification service).

Once per season, at forecast time. Re-running for a revised forecast is safe:
the cache key includes the payload hash, so a corrected number misses the cache
and regenerates rather than serving stale advice.

Storage is intentionally not implemented here -- Platform owns persistence. Any
callable taking an Advisory can be registered:

    from src.advisory.trigger import register_sink, on_prediction_complete
    register_sink(save_advisory_to_db)
    register_sink(queue_sms)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from .cache import AdvisoryCache
from .generator import generate_advisory, load_llm_config
from .schemas import Advisory, PredictionPayload

logger = logging.getLogger(__name__)

Sink = Callable[[Advisory], None]
_sinks: List[Sink] = []

_cache = AdvisoryCache(
    ttl_seconds=load_llm_config()["cache"]["ttl_seconds"],
    max_entries=load_llm_config()["cache"]["max_entries"],
)


def register_sink(sink: Sink) -> None:
    """Register a destination for generated advisories."""
    if sink not in _sinks:
        _sinks.append(sink)


def clear_sinks() -> None:
    _sinks.clear()


def on_prediction_complete(
    prediction: Dict[str, Any], *, lang: Optional[str] = None
) -> Advisory:
    """Generate the seasonal advisory for a completed forecast and fan it out.

    A failing sink is logged and skipped: one broken downstream service must not
    stop the others from receiving the advisory, and must not lose it entirely.
    """
    payload = PredictionPayload.from_dict(prediction)
    advisory = generate_advisory(payload, lang=lang, cache=_cache)

    logger.info(
        "advisory generated for %s (%s, band=%s, via=%s)",
        advisory.field_id,
        advisory.lang,
        advisory.verdict.band,
        advisory.generated_by,
    )

    for sink in _sinks:
        try:
            sink(advisory)
        except Exception:  # noqa: BLE001 - one bad sink must not lose the advisory
            logger.exception(
                "advisory sink %s failed for %s",
                getattr(sink, "__name__", repr(sink)),
                advisory.field_id,
            )

    return advisory
