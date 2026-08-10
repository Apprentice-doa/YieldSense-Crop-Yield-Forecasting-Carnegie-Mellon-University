"""Tests for advisory generation: providers, validation, cache, fallback.

Every test here runs offline. FakeProvider scripts the model's behaviour, so we
can assert what happens on a timeout, on malformed JSON, on an invented yield
figure, and on a banned topic -- none of which we could trigger reliably against
a real API.

The guarantee under test: **generation cannot fail to produce an advisory.**
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.advisory.cache import AdvisoryCache, advisory_cache_key
from src.advisory.generator import build_user_prompt, generate_advisory
from src.advisory.providers import FakeProvider, LLMError
from src.advisory.rules import build_verdict, load_config
from src.advisory.schemas import PredictionPayload
from src.advisory.validation import (
    check_band_consistency,
    check_numeric_fidelity,
    check_safety,
    check_shape,
    check_substance,
    validate_response,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "advisory"


@pytest.fixture(autouse=True)
def no_backoff_sleep(monkeypatch):
    """Retry backoff is real in production and pointless in CI."""
    monkeypatch.setattr("src.advisory.generator.time.sleep", lambda _s: None)


@pytest.fixture(scope="module")
def rules():
    return load_config()[0]


@pytest.fixture
def payload():
    return PredictionPayload.from_dict(
        json.loads((FIXTURE_DIR / "band_critical.json").read_text(encoding="utf-8"))
    )


@pytest.fixture
def verdict(payload):
    return build_verdict(payload)


@pytest.fixture
def cache():
    return AdvisoryCache(ttl_seconds=100, max_entries=10)


def good_response(verdict):
    """A response that should pass every check."""
    return {
        "headline": f"{verdict.crop_type} is tracking below a typical season",
        "body": (
            f"Your {verdict.crop_type} is estimated at "
            f"{verdict.predicted_yield:g} {verdict.yield_unit}, which is lower "
            "than what we usually record for this crop. Rain has been light and "
            "the crop is less green than we would expect."
        ),
        "actions": [a.action for a in verdict.actions],
    }


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #
def test_valid_llm_response_is_used(payload, verdict):
    provider = FakeProvider([good_response(verdict)])
    advisory = generate_advisory(payload, providers=[provider], use_cache=False)

    assert advisory.generated_by == "llm"
    assert advisory.llm_model == "fake:fake-1"
    assert advisory.headline
    assert "What to do:" in advisory.body
    assert len(provider.calls) == 1


def test_sms_is_always_rules_rendered_even_when_llm_succeeds(payload, verdict, rules):
    """SMS must stay deterministic and free: the LLM never writes it."""
    from src.advisory.rules import render_sms

    provider = FakeProvider([good_response(verdict)])
    advisory = generate_advisory(payload, providers=[provider], use_cache=False)
    assert advisory.sms_text == render_sms(verdict, rules)
    assert len(advisory.sms_text) <= rules["delivery"]["sms_max_chars"]


# --------------------------------------------------------------------------- #
# Fallback: generation cannot fail
# --------------------------------------------------------------------------- #
def test_no_provider_configured_still_produces_an_advisory(payload):
    advisory = generate_advisory(payload, providers=[], use_cache=False)
    assert advisory.generated_by == "rules"
    assert advisory.headline and advisory.body and advisory.sms_text


def test_provider_outage_falls_back_to_rules(payload):
    provider = FakeProvider(
        [
            LLMError("connection reset", retryable=True),
            LLMError("connection reset", retryable=True),
        ]
    )
    advisory = generate_advisory(payload, providers=[provider], use_cache=False)
    assert advisory.generated_by == "llm_fallback_rules"
    assert advisory.body.strip()


def test_second_provider_is_tried_when_first_fails(payload, verdict):
    dead = FakeProvider([LLMError("503 upstream", retryable=True)] * 2)
    alive = FakeProvider([good_response(verdict)])
    advisory = generate_advisory(payload, providers=[dead, alive], use_cache=False)

    assert advisory.generated_by == "llm"
    assert len(alive.calls) == 1


def test_malformed_json_falls_back(payload):
    provider = FakeProvider([LLMError("response was not valid JSON")] * 2)
    advisory = generate_advisory(payload, providers=[provider], use_cache=False)
    assert advisory.generated_by == "llm_fallback_rules"


def test_non_retryable_error_does_not_retry_the_same_provider(payload):
    provider = FakeProvider(
        [LLMError("GEMINI_API_KEY is not set", retryable=False), {"unused": True}]
    )
    generate_advisory(payload, providers=[provider], use_cache=False)
    assert len(provider.calls) == 1, "a missing API key must not be retried"


# --------------------------------------------------------------------------- #
# Repair retry
# --------------------------------------------------------------------------- #
def test_invalid_response_triggers_a_repair_retry_that_can_succeed(payload, verdict):
    bad = good_response(verdict)
    bad["body"] += " Farmers nearby harvested 999 bags last season."
    provider = FakeProvider([bad, good_response(verdict)])

    advisory = generate_advisory(payload, providers=[provider], use_cache=False)

    assert advisory.generated_by == "llm"
    assert len(provider.calls) == 2
    second_prompt = provider.calls[1]["user"]
    assert "previous attempt was rejected" in second_prompt
    assert "999" in second_prompt, "the repair hint must name the offending figure"


def test_repeated_invalid_responses_fall_back_to_rules(payload, verdict):
    bad = good_response(verdict)
    bad["body"] += " Expect 4200 kg per hectare."
    provider = FakeProvider([bad, bad])

    advisory = generate_advisory(payload, providers=[provider], use_cache=False)

    assert advisory.generated_by == "llm_fallback_rules"
    assert "4200" not in advisory.body


def test_cost_guard_caps_total_llm_calls(payload, verdict):
    """Four providers each willing to retry must not mean eight calls."""
    from src.advisory.generator import load_llm_config

    cap = load_llm_config()["cost_guard"]["max_llm_calls_per_advisory"]
    bad = good_response(verdict)
    bad["headline"] = "x" * 200  # always fails the shape check
    providers = [FakeProvider([bad] * 8) for _ in range(4)]

    generate_advisory(payload, providers=providers, use_cache=False)

    total = sum(len(p.calls) for p in providers)
    assert total <= cap, f"cost guard breached: {total} calls, cap is {cap}"


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def test_numeric_fidelity_rejects_an_invented_figure(verdict):
    errors = check_numeric_fidelity("You should expect 812 bags this year.", verdict)
    assert errors and "812" in errors[0]


def test_numeric_fidelity_accepts_verdict_numbers(verdict):
    text = f"Estimated at {verdict.predicted_yield:g} {verdict.yield_unit}."
    assert check_numeric_fidelity(text, verdict) == []


@pytest.mark.parametrize("rendering", ["90%", "90.1%", "0.901"])
def test_numeric_fidelity_accepts_faithful_renderings_of_a_ratio(rendering, verdict):
    """Regression: accepting only "90" discarded a correct advisory that said 90.1%.

    A ratio of 0.901 is faithfully stated as 0.901, 90% or 90.1%. Rejecting the
    one-decimal form sent a good advisory to the rules fallback in the live eval.
    """
    verdict.baseline_ratio = 0.901
    assert check_numeric_fidelity(f"That is about {rendering} of typical.", verdict) == []


def test_numeric_fidelity_still_rejects_a_nearby_invention(verdict):
    """Widening the tolerance must not turn the check off."""
    verdict.baseline_ratio = 0.901
    assert check_numeric_fidelity("That is about 73.4% of typical.", verdict)


def test_numeric_fidelity_ignores_the_field_identifier(verdict):
    assert check_numeric_fidelity(f"Field {verdict.field_id} looks dry.", verdict) == []


@pytest.mark.parametrize(
    "text",
    [
        "Apply urea at planting.",
        "Spray for stem borer this week.",
        "Consider a loan to cover inputs.",
        "This is below your five-year average.",
        "We guarantee a better harvest.",
    ],
)
def test_safety_check_catches_banned_content(text, rules):
    assert check_safety(text, rules), f"should have been rejected: {text}"


def test_safety_check_passes_ordinary_advice(rules):
    assert (
        check_safety("Scout the field on foot and check for dry patches.", rules) == []
    )


def test_shape_check_enforces_limits(rules):
    limits = {"headline_max_chars": 80, "body_max_chars": 900}
    assert check_shape({"headline": "ok", "body": "ok", "actions": ["a"]}, limits) == []
    assert check_shape({"body": "ok", "actions": []}, limits)
    assert check_shape({"headline": "x" * 200, "body": "ok", "actions": []}, limits)
    assert check_shape({"headline": "ok", "body": "ok", "actions": [""]}, limits)


def test_substance_check_rejects_added_or_dropped_actions(verdict):
    correct = {"actions": [a.action for a in verdict.actions]}
    assert check_substance(correct, verdict) == []

    extra = {"actions": [a.action for a in verdict.actions] + ["Buy more seed."]}
    assert check_substance(extra, verdict)

    assert check_substance({"actions": []}, verdict)


def test_band_consistency_rejects_softening_bad_news(verdict):
    assert verdict.band == "critical"
    softened = {
        "headline": "Your season is on track",
        "body": "Everything looks as expected.",
    }
    assert check_band_consistency(softened, verdict)

    honest = {
        "headline": "Yield is below what we usually record",
        "body": "Expect a smaller harvest than normal.",
    }
    assert check_band_consistency(honest, verdict) == []


def test_validate_response_reports_every_problem_at_once(verdict, rules):
    limits = {"headline_max_chars": 80, "body_max_chars": 900}
    result = validate_response(
        {
            "headline": "Season update",
            "body": "Apply urea and expect 999 bags.",
            "actions": [],
        },
        verdict,
        rules,
        limits,
    )
    assert not result.ok
    assert len(result.errors) >= 3, result.errors
    assert result.repair_hint().startswith("- ")


# --------------------------------------------------------------------------- #
# Cache
# --------------------------------------------------------------------------- #
def test_cache_key_is_stable_across_dict_ordering():
    a = {"field_id": "F1", "crop_type": "Maize", "predicted_yield": 40.0}
    b = {"predicted_yield": 40.0, "crop_type": "Maize", "field_id": "F1"}
    assert advisory_cache_key(a, "0.1.0", "en") == advisory_cache_key(b, "0.1.0", "en")


def test_cache_key_changes_with_rules_version_and_language():
    p = {"field_id": "F1", "predicted_yield": 40.0}
    base = advisory_cache_key(p, "0.1.0", "en")
    assert base != advisory_cache_key(p, "0.2.0", "en")
    assert base != advisory_cache_key(p, "0.1.0", "sw")


def test_revised_forecast_misses_the_cache():
    """A corrected number must never serve the old advisory."""
    original = {"field_id": "F1", "predicted_yield": 40.0}
    revised = {"field_id": "F1", "predicted_yield": 31.5}
    assert advisory_cache_key(original, "0.1.0", "en") != advisory_cache_key(
        revised, "0.1.0", "en"
    )


def test_second_request_is_served_from_cache_without_calling_the_llm(
    payload, verdict, cache
):
    provider = FakeProvider([good_response(verdict)])

    first = generate_advisory(payload, providers=[provider], cache=cache)
    second = generate_advisory(payload, providers=[provider], cache=cache)

    assert len(provider.calls) == 1, "second request must not hit the provider"
    assert second.headline == first.headline
    assert cache.stats()["hits"] == 1


def test_cache_respects_ttl():
    c = AdvisoryCache(ttl_seconds=10, max_entries=10)
    c.set("k", {"headline": "h"}, now=1000.0)
    assert c.get("k", now=1005.0) is not None
    assert c.get("k", now=1011.0) is None


def test_cache_evicts_least_recently_used():
    c = AdvisoryCache(ttl_seconds=1000, max_entries=2)
    c.set("a", {"v": 1})
    c.set("b", {"v": 2})
    c.get("a")  # 'a' becomes most recent
    c.set("c", {"v": 3})  # evicts 'b'
    assert c.get("a") is not None
    assert c.get("b") is None
    assert c.get("c") is not None


def test_transient_outage_is_not_cached(payload, cache, verdict):
    """A provider blip must not pin the rules fallback for 90 days."""
    dead = FakeProvider([LLMError("503", retryable=True)] * 2)
    first = generate_advisory(payload, providers=[dead], cache=cache)
    assert first.generated_by == "llm_fallback_rules"

    alive = FakeProvider([good_response(verdict)])
    second = generate_advisory(payload, providers=[alive], cache=cache)
    assert second.generated_by == "llm", "recovery must not be blocked by cache"


# --------------------------------------------------------------------------- #
# Provider wiring
# --------------------------------------------------------------------------- #
class _FakeResponse:
    status_code = 200

    def json(self):
        return {"choices": [{"message": {"content": '{"ok": true}'}}]}


@pytest.fixture
def capture_post(monkeypatch):
    """Intercept the HTTP call and hand back what would have been sent."""
    sent = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.update(url=url, headers=headers, payload=json, timeout=timeout)
        return _FakeResponse()

    monkeypatch.setattr(
        "src.advisory.providers.http_providers.requests.post", fake_post
    )
    return sent


def test_openai_provider_defaults_to_max_tokens(capture_post, monkeypatch):
    from src.advisory.providers.http_providers import OpenAIProvider

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    provider = OpenAIProvider(
        {
            "name": "openai",
            "model": "gpt-4o-mini",
            "endpoint": "https://x/v1/chat/completions",
        },
        {"temperature": 0.3, "max_output_tokens": 800},
    )
    provider.generate_json("sys", "user")

    assert "max_tokens" in capture_post["payload"]
    assert "max_completion_tokens" not in capture_post["payload"]
    assert capture_post["payload"]["temperature"] == 0.3


def test_token_param_can_be_overridden_for_newer_models(capture_post, monkeypatch):
    """The Azure gpt-5.2 deployment rejects `max_tokens` outright."""
    from src.advisory.providers.http_providers import OpenAIProvider

    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    provider = OpenAIProvider(
        {
            "name": "azure_openai",
            "model": "gpt-5.2",
            "endpoint": "https://x/openai/v1/chat/completions",
            "api_key_env": "AZURE_OPENAI_API_KEY",
            "token_param": "max_completion_tokens",
        },
        {"max_output_tokens": 800},
    )
    provider.generate_json("sys", "user")

    assert capture_post["payload"]["max_completion_tokens"] == 800
    assert "max_tokens" not in capture_post["payload"]
    assert provider.name == "azure_openai"


def test_temperature_can_be_suppressed(capture_post, monkeypatch):
    from src.advisory.providers.http_providers import OpenAIProvider

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    provider = OpenAIProvider(
        {"model": "m", "endpoint": "https://x", "send_temperature": False},
        {"temperature": 0.3},
    )
    provider.generate_json("sys", "user")
    assert "temperature" not in capture_post["payload"]


def test_endpoint_and_model_come_from_env_when_set(monkeypatch):
    """Tenant resource and deployment names must not need committing."""
    from src.advisory.providers.http_providers import OpenAIProvider

    monkeypatch.setenv(
        "AZURE_OPENAI_ENDPOINT", "https://real.services.ai.azure.com/openai/v1"
    )
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "my-deployment")
    provider = OpenAIProvider(
        {
            "model": "placeholder",
            "model_env": "AZURE_OPENAI_DEPLOYMENT",
            "endpoint": "https://REPLACE-ME/chat/completions",
            "endpoint_env": "AZURE_OPENAI_ENDPOINT",
        },
        {},
    )
    assert (
        provider.endpoint
        == "https://real.services.ai.azure.com/openai/v1/chat/completions"
    )
    assert provider.model == "my-deployment"


def test_config_endpoint_is_used_when_env_is_absent(monkeypatch):
    from src.advisory.providers.http_providers import OpenAIProvider

    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    provider = OpenAIProvider(
        {
            "model": "m",
            "endpoint": "https://configured/chat/completions",
            "endpoint_env": "AZURE_OPENAI_ENDPOINT",
        },
        {},
    )
    assert provider.endpoint == "https://configured/chat/completions"


def test_azure_provider_is_registered():
    from src.advisory.providers.http_providers import PROVIDER_TYPES, OpenAIProvider

    assert PROVIDER_TYPES["azure_openai"] is OpenAIProvider


def test_configured_providers_all_resolve(monkeypatch):
    """Every block in advisory_llm.yaml must build into a real provider."""
    from src.advisory.generator import load_llm_config
    from src.advisory.providers import build_provider

    llm_config = load_llm_config()
    for block in llm_config["providers"]:
        assert build_provider(block, llm_config["generation"]) is not None, block[
            "name"
        ]


# --------------------------------------------------------------------------- #
# Prompt assembly
# --------------------------------------------------------------------------- #
def test_prompt_carries_the_verdict_and_permitted_numbers(verdict, rules):
    prompt = build_user_prompt(verdict, "en", rules)
    assert verdict.crop_type in prompt
    assert f"{verdict.predicted_yield:g}" in prompt
    assert "Only these values may appear" in prompt
    assert "{" not in prompt.split("```json")[0], "template placeholder left unfilled"


def test_prompt_flags_low_confidence(rules, payload):
    wide = PredictionPayload.from_dict(
        json.loads(
            (FIXTURE_DIR / "edge_wide_interval.json").read_text(encoding="utf-8")
        )
    )
    prompt = build_user_prompt(build_verdict(wide), "en", rules)
    assert "uncertain" in prompt.lower()


def test_prompt_flags_data_quality_problems(rules):
    bad = PredictionPayload.from_dict(
        json.loads((FIXTURE_DIR / "edge_invalid_ndvi.json").read_text(encoding="utf-8"))
    )
    prompt = build_user_prompt(build_verdict(bad), "en", rules)
    assert "missing or unusable" in prompt


@pytest.mark.parametrize(
    "lang,name", [("sw", "Kiswahili"), ("rw", "Kinyarwanda"), ("fr", "French")]
)
def test_prompt_names_the_target_language(lang, name, verdict, rules):
    assert name in build_user_prompt(verdict, lang, rules)
