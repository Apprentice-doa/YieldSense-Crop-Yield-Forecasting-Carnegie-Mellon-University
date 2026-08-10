"""GenAI Advisory track.

Turns a yield prediction into a farmer-facing recommendation, once per season,
at forecast time.

Design rule, enforced by tests: the rules engine decides every number, band and
quantity; the LLM only rephrases and translates what the rules already decided.
See docs/ADVISORY.md.
"""

from .rules import advise, build_verdict, render_rules_advisory, render_sms
from .schemas import (
    SCHEMA_VERSION,
    Action,
    Advisory,
    PostHarvestPlan,
    PredictionPayload,
    Verdict,
)

__all__ = [
    "advise",
    "build_verdict",
    "render_rules_advisory",
    "render_sms",
    "Action",
    "Advisory",
    "PostHarvestPlan",
    "PredictionPayload",
    "Verdict",
    "SCHEMA_VERSION",
]
