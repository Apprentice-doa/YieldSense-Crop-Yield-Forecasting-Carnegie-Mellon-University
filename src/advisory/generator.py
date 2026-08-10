"""Advisory generation: verdict -> prompt -> LLM -> validate -> advisory.

The whole point of this module is that it cannot fail to produce an advisory.
Every path -- no API key, provider down, malformed JSON, invented numbers,
banned topic, budget exhausted -- ends at the rules-only renderer, which is
already a complete, sendable advisory.

Escalation order for one request:

    cache hit                                   -> return
    provider 1, attempt 1                       -> validate -> return if clean
    provider 1, attempt 2 (repair, with errors) -> validate -> return if clean
    provider 2, attempts 1..2                   -> validate -> return if clean
    rules-only advisory                         -> always succeeds

`generated_by` on the returned Advisory records which path was taken, so D5-D6
can measure how often the LLM path actually holds.
"""

from __future__ import annotations

import functools
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .cache import AdvisoryCache, advisory_cache_key
from .providers import LLMError, LLMProvider, build_provider, has_credentials
from .rules import build_verdict, load_config, render_rules_advisory, render_sms
from .schemas import Advisory, PredictionPayload, Verdict
from .validation import ValidationResult, validate_response

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
LLM_CONFIG_PATH = REPO_ROOT / "configs" / "advisory_llm.yaml"
PROMPT_DIR = Path(__file__).resolve().parent / "prompts"

LANGUAGE_NAMES = {
    "en": "English",
    "sw": "Kiswahili",
    "rw": "Kinyarwanda",
    "fr": "French",
}


@functools.lru_cache(maxsize=2)
def load_llm_config(path: str = str(LLM_CONFIG_PATH)) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@functools.lru_cache(maxsize=8)
def load_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Prompt assembly
# --------------------------------------------------------------------------- #
def build_user_prompt(
    verdict: Verdict, lang: str, rules: Dict[str, Any], repair_hint: str = ""
) -> str:
    import json

    facts = verdict.numeric_facts()
    low_confidence_note = (
        "The estimate is uncertain. Say so plainly and avoid firm predictions."
        if verdict.confidence == "low"
        else ""
    )
    data_quality_note = (
        "Some sensor readings for this field were missing or unusable, so parts "
        "of the picture are incomplete. Do not speculate about what they showed."
        if verdict.data_quality_flags
        else ""
    )

    prompt = load_prompt("advisory_user.md").format(
        verdict_json=json.dumps(verdict.to_dict(), indent=2, default=str),
        numeric_facts=", ".join(f"{v:g}" for v in facts),
        language_name=LANGUAGE_NAMES.get(lang, lang),
        lang=lang,
        crop_type=verdict.crop_type,
        band_label=verdict.band_label,
        confidence=verdict.confidence,
        max_actions=len(verdict.actions),
        low_confidence_note=low_confidence_note,
        data_quality_note=data_quality_note,
    )

    if repair_hint:
        prompt += (
            "\n\n# Your previous attempt was rejected\n\n"
            "Fix exactly these problems and return the corrected JSON:\n\n"
            f"{repair_hint}\n"
        )
    return prompt


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #
def _providers_for(
    llm_config: Dict[str, Any], override: Optional[List[LLMProvider]]
) -> List[LLMProvider]:
    if override is not None:
        return override

    providers = []
    for block in llm_config.get("providers", []):
        if not has_credentials(block):
            logger.info(
                "advisory: skipping provider %s, %s not set",
                block.get("name"),
                block.get("api_key_env"),
            )
            continue
        provider = build_provider(block, llm_config["generation"])
        if provider is not None:
            providers.append(provider)
    return providers


def _try_provider(
    provider: LLMProvider,
    verdict: Verdict,
    lang: str,
    rules: Dict[str, Any],
    llm_config: Dict[str, Any],
    calls_remaining: List[int],
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Attempt generation with one provider, with a repair retry. Returns (response, failures)."""
    system = load_prompt("system.md")
    limits = llm_config["limits"]
    gen = llm_config["generation"]
    max_attempts = gen.get("max_attempts_per_provider", 2)
    backoff = gen.get("backoff_seconds", [1, 3])

    failures: List[str] = []
    repair_hint = ""

    for attempt in range(max_attempts):
        if calls_remaining[0] <= 0:
            failures.append("cost guard: no LLM calls left for this advisory")
            return None, failures

        calls_remaining[0] -= 1
        user = build_user_prompt(verdict, lang, rules, repair_hint)

        try:
            response = provider.generate_json(system, user)
        except LLMError as exc:
            failures.append(f"{provider.name} attempt {attempt + 1}: {exc}")
            if not exc.retryable or attempt == max_attempts - 1:
                return None, failures
            time.sleep(backoff[min(attempt, len(backoff) - 1)])
            continue

        result: ValidationResult = validate_response(response, verdict, rules, limits)
        if result.ok:
            return response, failures

        failures.append(
            f"{provider.name} attempt {attempt + 1} failed validation: "
            f"{'; '.join(result.errors)}"
        )
        repair_hint = result.repair_hint()

    return None, failures


def generate_advisory(
    payload: PredictionPayload,
    *,
    lang: Optional[str] = None,
    providers: Optional[List[LLMProvider]] = None,
    cache: Optional[AdvisoryCache] = None,
    use_cache: bool = True,
) -> Advisory:
    """Produce an advisory for one forecast. Never raises on provider failure.

    `providers` is injectable so tests can drive the whole path with
    FakeProvider and no network.
    """
    rules, _ = load_config()
    llm_config = load_llm_config()
    lang = lang or payload.farmer_lang or rules["delivery"]["default_language"]

    verdict = build_verdict(payload)

    cache_enabled = use_cache and llm_config["cache"]["enabled"] and cache is not None
    key = advisory_cache_key(payload.to_dict(), verdict.rules_version, lang)
    if cache_enabled:
        cached = cache.get(key)
        if cached is not None:
            logger.info("advisory: cache hit for %s", payload.field_id)
            return _advisory_from_cached(cached, verdict, rules)

    active = _providers_for(llm_config, providers)
    all_failures: List[str] = []
    calls_remaining = [llm_config["cost_guard"]["max_llm_calls_per_advisory"]]

    for provider in active:
        response, failures = _try_provider(
            provider, verdict, lang, rules, llm_config, calls_remaining
        )
        all_failures.extend(failures)
        if response is not None:
            advisory = _advisory_from_response(response, verdict, rules, lang, provider)
            if cache_enabled:
                cache.set(key, _cacheable(advisory))
            return advisory

    if all_failures:
        logger.warning(
            "advisory: falling back to rules for %s after %d failure(s): %s",
            payload.field_id,
            len(all_failures),
            " | ".join(all_failures),
        )
    else:
        logger.info(
            "advisory: no LLM provider configured, using rules text for %s",
            payload.field_id,
        )

    fallback = render_rules_advisory(verdict, rules)
    fallback.generated_by = "llm_fallback_rules" if active else "rules"
    fallback.lang = "en"  # rules copy is authored in English only
    if cache_enabled and not active:
        # Cache the no-provider case; do not cache a transient provider outage.
        cache.set(key, _cacheable(fallback))
    return fallback


def _advisory_from_response(
    response: Dict[str, Any],
    verdict: Verdict,
    rules: Dict[str, Any],
    lang: str,
    provider: LLMProvider,
) -> Advisory:
    body = response["body"].strip()
    actions = response.get("actions") or []
    if actions:
        body = body + "\n\nWhat to do:\n" + "\n".join(f"- {a}" for a in actions)

    return Advisory(
        field_id=verdict.field_id,
        lang=lang,
        headline=response["headline"].strip(),
        body=body,
        # SMS is always rules-rendered: deterministic, free, and exactly 160 chars.
        sms_text=render_sms(verdict, rules),
        verdict=verdict,
        disclaimer=rules["safety"]["disclaimer"],
        generated_by="llm",
        llm_model=f"{provider.name}:{provider.model}",
    )


def _cacheable(advisory: Advisory) -> Dict[str, Any]:
    return {
        "headline": advisory.headline,
        "body": advisory.body,
        "sms_text": advisory.sms_text,
        "lang": advisory.lang,
        "generated_by": advisory.generated_by,
        "llm_model": advisory.llm_model,
    }


def _advisory_from_cached(
    cached: Dict[str, Any], verdict: Verdict, rules: Dict[str, Any]
) -> Advisory:
    return Advisory(
        field_id=verdict.field_id,
        lang=cached["lang"],
        headline=cached["headline"],
        body=cached["body"],
        sms_text=cached["sms_text"],
        verdict=verdict,
        disclaimer=rules["safety"]["disclaimer"],
        generated_by=cached["generated_by"],
        llm_model=cached.get("llm_model"),
    )
