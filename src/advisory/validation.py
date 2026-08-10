"""Validation of generated advisory text.

This module is the reason the LLM can be trusted with farmer-facing copy. Every
generated response passes through here before it can reach anyone; a failure
triggers one repair retry and then the rules-only fallback.

Four independent checks:

    shape     -- the response is the object we asked for
    numeric   -- every figure traces back to the verdict
    safety    -- no banned topic slipped in
    substance -- the actions still match what the rules decided

The numeric check is the important one. It is the same assertion the D1-D2 tests
run against the rules renderer, applied to LLM output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .schemas import Verdict

NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")

# Phrases that claim an authority our single-season baseline does not have.
FORBIDDEN_CLAIMS = [
    "five-year",
    "5-year",
    "five year",
    "district average",
    "national average",
    "historical average",
    "last year",
    "guarantee",
    "guaranteed",
]

# Coarse but effective: banned-topic terms that must never appear in copy.
BANNED_TERMS = [
    "mg/l",
    "ml per",
    "kg per acre of fertilis",
    "kg per hectare of fertilis",
    "apply urea",
    "apply npk",
    "spray ",
    "pesticide",
    "herbicide",
    "insecticide",
    "fungicide",
    "loan",
    "credit",
    "interest rate",
    "title deed",
    "land right",
]


@dataclass
class ValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)

    def repair_hint(self) -> str:
        """Feedback for the repair retry: specific, so the model can act on it."""
        return "\n".join(f"- {e}" for e in self.errors)


def _tolerated_number_forms(value: float) -> set:
    """Every string form of a verdict number we accept in prose."""
    forms = {
        f"{value:g}",
        f"{round(value):g}",
        f"{value:.1f}".rstrip("0").rstrip("."),
        f"{value:.2f}".rstrip("0").rstrip("."),
    }
    # Percentages: the rules renderer states the baseline ratio as e.g. "68%".
    if 0 < value < 10:
        forms.add(f"{round(value * 100):g}")
    return {f for f in forms if f}


def check_numeric_fidelity(text: str, verdict: Verdict) -> List[str]:
    """Every number in `text` must be a verdict fact.

    Identifiers are stripped first: "Field_1" is a name, not a claim about the
    crop. Years are tolerated because a date is not a yield figure.
    """
    allowed: set = set()
    for value in verdict.numeric_facts():
        allowed |= _tolerated_number_forms(float(value))

    scrubbed = text.replace(verdict.field_id, " ")
    scrubbed = re.sub(r"\b(19|20)\d{2}\b", " ", scrubbed)  # years

    errors = []
    for token in NUMBER_RE.findall(scrubbed):
        normalised = token.replace(",", ".")
        if normalised not in allowed and token not in allowed:
            errors.append(
                f"the figure '{token}' is not in the verdict; remove it or use "
                f"only these values: {sorted(allowed)}"
            )
    return errors


def check_safety(text: str, rules: Dict[str, Any]) -> List[str]:
    lowered = text.lower()
    errors = []
    for term in BANNED_TERMS:
        if term in lowered:
            errors.append(
                f"'{term.strip()}' touches a banned topic; refer the farmer to "
                f"their {rules['safety']['defer_to']} instead"
            )
    for claim in FORBIDDEN_CLAIMS:
        if claim in lowered:
            errors.append(
                f"'{claim}' claims an authority our data does not have; the "
                f"baseline is a single-season average from our own records"
            )
    return errors


def check_shape(response: Dict[str, Any], limits: Dict[str, Any]) -> List[str]:
    errors = []
    for key in ("headline", "body", "actions"):
        if key not in response:
            errors.append(f"missing required key '{key}'")

    headline = response.get("headline")
    if headline is not None:
        if not isinstance(headline, str) or not headline.strip():
            errors.append("'headline' must be a non-empty string")
        elif len(headline) > limits["headline_max_chars"]:
            errors.append(
                f"'headline' is {len(headline)} characters, limit is "
                f"{limits['headline_max_chars']}"
            )

    body = response.get("body")
    if body is not None:
        if not isinstance(body, str) or not body.strip():
            errors.append("'body' must be a non-empty string")
        elif len(body) > limits["body_max_chars"]:
            errors.append(
                f"'body' is {len(body)} characters, limit is "
                f"{limits['body_max_chars']}"
            )

    actions = response.get("actions")
    if actions is not None and (
        not isinstance(actions, list)
        or not all(isinstance(a, str) and a.strip() for a in actions)
    ):
        errors.append("'actions' must be a list of non-empty strings")

    return errors


def check_substance(response: Dict[str, Any], verdict: Verdict) -> List[str]:
    """The model may rephrase actions; it may not add, drop or reorder them."""
    actions = response.get("actions")
    if not isinstance(actions, list):
        return []  # already reported by check_shape

    expected = len(verdict.actions)
    if len(actions) != expected:
        return [
            f"returned {len(actions)} actions but the verdict has {expected}; "
            f"restate each verdict action exactly once, in the same order"
        ]
    return []


def check_band_consistency(response: Dict[str, Any], verdict: Verdict) -> List[str]:
    """A below-typical forecast must not be narrated as good news."""
    if verdict.band not in ("critical", "below"):
        return []
    text = f"{response.get('headline', '')} {response.get('body', '')}".lower()
    reassuring = ("on track", "as expected", "normal season", "good season", "above")
    if any(phrase in text for phrase in reassuring) and not any(
        word in text for word in ("below", "less", "lower", "smaller")
    ):
        return [
            "the verdict says yield is below typical; the advisory must say so "
            "plainly rather than softening it"
        ]
    return []


def validate_response(
    response: Dict[str, Any],
    verdict: Verdict,
    rules: Dict[str, Any],
    limits: Dict[str, Any],
) -> ValidationResult:
    """Run every check. Order matters only for readability of the repair hint."""
    errors: List[str] = []
    errors += check_shape(response, limits)

    text = " ".join(str(response.get(k, "")) for k in ("headline", "body"))
    actions = response.get("actions")
    if isinstance(actions, list):
        text += " " + " ".join(str(a) for a in actions)

    errors += check_numeric_fidelity(text, verdict)
    errors += check_safety(text, rules)
    errors += check_substance(response, verdict)
    errors += check_band_consistency(response, verdict)

    return ValidationResult(ok=not errors, errors=errors)
