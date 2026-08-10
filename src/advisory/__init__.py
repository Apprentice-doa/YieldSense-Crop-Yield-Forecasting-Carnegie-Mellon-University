"""GenAI Advisory track.

Turns a yield prediction into a farmer-facing recommendation, once per season,
at forecast time.

Design rule, enforced by tests: the rules engine decides every number, band and
quantity; the LLM only rephrases and translates what the rules already decided.
See docs/ADVISORY.md.

Note: `api` is not imported here. It requires FastAPI, and the rules engine must
stay importable in CI, notebooks and the SMS worker without a web framework.
Import it explicitly with `from src.advisory.api import router`.
"""

from .cache import AdvisoryCache, advisory_cache_key
from .generator import generate_advisory
from .rules import advise, build_verdict, render_rules_advisory, render_sms
from .schemas import (
    SCHEMA_VERSION,
    Action,
    Advisory,
    PostHarvestPlan,
    PredictionPayload,
    Verdict,
)
from .trigger import on_prediction_complete, register_sink
from .validation import validate_response

__all__ = [
    "advise",
    "build_verdict",
    "generate_advisory",
    "on_prediction_complete",
    "register_sink",
    "render_rules_advisory",
    "render_sms",
    "validate_response",
    "Action",
    "Advisory",
    "AdvisoryCache",
    "advisory_cache_key",
    "PostHarvestPlan",
    "PredictionPayload",
    "Verdict",
    "SCHEMA_VERSION",
]
