"""Sanitisation of free-text payload fields.

`field_id`, `crop_type` and `region` arrive from upstream and end up in two
places that matter: serialised into the LLM prompt, and rendered directly into
farmer-facing text by the rules renderer.

A red-team run found the second one is the more dangerous. An injection payload
in `crop_type` caused the provider's own content filter to reject the call, the
generator fell back to the rules renderer as designed -- and the rules renderer
echoed the attacker's text straight into the headline and the SMS. The
deterministic path, which is our safety net for every other failure, was the one
that leaked. Blocking the LLM is not sufficient protection when the fallback
prints the input.

Defence is structural rather than pattern-matching:

1. **Character allowlist.** No newlines, quotes, braces or backticks survive, so
   nothing in these fields can close a JSON string or open a new prompt section.
2. **Hard length cap.** Real crop names are short. 32 characters cannot carry an
   instruction, and the cap applies before anything is rendered.
3. **Phrase detection** on top, replacing an obvious injection with a
   placeholder and raising a data-quality flag, so the attempt is visible in
   logs rather than silently truncated.

Layer 3 alone would be a blocklist and therefore bypassable. Layers 1 and 2 do
the real work; layer 3 exists so we can see it happening.
"""

from __future__ import annotations

import re
import unicodedata
from typing import List, Optional, Tuple

# Per-field character allowlists. Narrower than one shared rule, because the
# fields are genuinely different shapes and the shared version leaked:
#
#   crop_type / region -- NO DIGITS. No real crop or place name contains one,
#     and a smuggled figure ("999999") rendered next to a yield in the headline
#     is exactly the invented-number failure the whole design exists to prevent.
#   field_id -- digits are legitimate ("Field_63") but spaces are not. Without
#     spaces the value can only ever read as one identifier token, never as a
#     sentence making a claim.
ALLOWED = {
    "field_id": re.compile(r"[^A-Za-z0-9_\-]"),
    "crop_type": re.compile(r"[^A-Za-z\s\-'()./]"),
    "region": re.compile(r"[^A-Za-z\s\-'().]"),
    "yield_unit": re.compile(r"[^A-Za-z0-9/%\s.\-]"),
}
DEFAULT_ALLOWED = re.compile(r"[^\w\s\-'./()]", re.UNICODE)
WHITESPACE = re.compile(r"\s+")

MAX_LENGTHS = {
    "field_id": 40,
    "crop_type": 32,
    "region": 60,
    "yield_unit": 16,
}

PLACEHOLDER = "Unknown"

# Not a security boundary -- the allowlist and length cap are. This exists to
# turn a silent truncation into a visible, logged event.
INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore\s+(all\s+)?(previous|prior|above)",
        r"disregard\s+(all\s+)?(previous|prior|the)",
        r"you\s+are\s+now\b",
        r"system\s*(prompt|message|instruction)",
        r"\bnew\s+instructions?\b",
        r"forget\s+(everything|all|your)",
        r"act\s+as\s+(a|an)\b",
        r"</?\s*(system|assistant|user)\s*>",
    )
]

LANG_RE = re.compile(r"^[a-z]{2}$")


def looks_like_injection(value: str) -> bool:
    return any(p.search(value) for p in INJECTION_PATTERNS)


def sanitize_text(
    value: Optional[str], field: str, max_length: Optional[int] = None
) -> Tuple[Optional[str], List[str]]:
    """Return (clean_value, flags). Never raises: bad input degrades, it does not 500."""
    if value is None:
        return None, []

    text = str(value)
    flags: List[str] = []

    if looks_like_injection(text):
        # Detected before truncation, since truncation could hide the giveaway.
        return PLACEHOLDER, [f"{field}:injection_attempt"]

    # Normalise first: NFKC folds look-alike characters that would otherwise
    # slip past the allowlist.
    text = unicodedata.normalize("NFKC", text)
    text = "".join(
        ch for ch in text if ch == " " or not unicodedata.category(ch).startswith("C")
    )

    stripped = ALLOWED.get(field, DEFAULT_ALLOWED).sub("", text)
    if stripped != text:
        flags.append(f"{field}:characters_removed")

    stripped = WHITESPACE.sub(" ", stripped).strip()

    limit = max_length or MAX_LENGTHS.get(field, 64)
    if len(stripped) > limit:
        stripped = stripped[:limit].rstrip()
        flags.append(f"{field}:truncated")

    if not stripped:
        return PLACEHOLDER, flags + [f"{field}:empty_after_sanitising"]

    return stripped, flags


def sanitize_lang(value: Optional[str], default: str = "en") -> Tuple[str, List[str]]:
    """Language codes are a closed set; anything else is not a language."""
    if not value:
        return default, []
    candidate = str(value).strip().lower()[:5]
    if LANG_RE.match(candidate):
        return candidate, []
    return default, ["farmer_lang:invalid"]
