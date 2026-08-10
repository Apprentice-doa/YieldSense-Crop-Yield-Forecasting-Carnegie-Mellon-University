"""Tests for the translation pass and the reviewed i18n config.

Translation is generate-in-English-then-translate, not generate-in-language.
The safety check matches English terms, so English is the only language we can
actually police; translation is confined to rephrasing copy that already passed
every gate. These tests hold that boundary.

All offline: FakeProvider plays both the generation and the translation call.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from src.advisory.generator import generate_advisory
from src.advisory.providers import FakeProvider, LLMError
from src.advisory.rules import (
    build_verdict,
    load_config,
    load_i18n,
    render_sms,
    strings_for,
)
from src.advisory.schemas import PredictionPayload
from src.advisory.validation import check_translation

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "advisory"
I18N_PATH = REPO_ROOT / "configs" / "advisory_i18n.yaml"

TRANSLATABLE = ["sw", "rw", "fr"]


@pytest.fixture(autouse=True)
def no_backoff_sleep(monkeypatch):
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


def english_response(verdict):
    return {
        "headline": f"{verdict.crop_type} is lower than we usually record",
        "body": (
            f"The estimate is {verdict.predicted_yield:g} {verdict.yield_unit}, "
            "lower than usual for this crop."
        ),
        "actions": [a.action for a in verdict.actions],
    }


def translated_response(verdict):
    """A plausible translation: same numbers, same action count, different words."""
    return {
        "headline": "Mavuno ni chini ya kawaida",
        "body": (
            f"Makadirio ni {verdict.predicted_yield:g} {verdict.yield_unit}, "
            "chini ya kawaida kwa zao hili."
        ),
        "actions": [f"[sw] {a.action}" for a in verdict.actions],
    }


# --------------------------------------------------------------------------- #
# The translation pass
# --------------------------------------------------------------------------- #
def test_english_is_generated_first_then_translated(payload, verdict):
    provider = FakeProvider([english_response(verdict), translated_response(verdict)])
    advisory = generate_advisory(
        payload, lang="sw", providers=[provider], use_cache=False
    )

    assert advisory.lang == "sw"
    assert advisory.generated_by == "llm"
    assert len(provider.calls) == 2, "one generation call, one translation call"
    assert "Mavuno" in advisory.headline


def test_english_request_makes_no_translation_call(payload, verdict):
    provider = FakeProvider([english_response(verdict)])
    advisory = generate_advisory(
        payload, lang="en", providers=[provider], use_cache=False
    )

    assert advisory.lang == "en"
    assert len(provider.calls) == 1


def test_failed_translation_serves_verified_english(payload, verdict):
    """Correct English beats a translation we could not verify."""
    provider = FakeProvider(
        [
            english_response(verdict),
            LLMError("translation service down", retryable=False),
        ]
    )
    advisory = generate_advisory(
        payload, lang="rw", providers=[provider], use_cache=False
    )

    assert advisory.lang == "en", "must not claim to be Kinyarwanda"
    assert advisory.generated_by == "llm"
    assert advisory.body.strip()


def test_translation_that_invents_a_number_is_rejected(payload, verdict):
    bad = translated_response(verdict)
    bad["body"] += " Utapata magunia 500."
    provider = FakeProvider([english_response(verdict), bad, bad])

    advisory = generate_advisory(
        payload, lang="sw", providers=[provider], use_cache=False
    )

    assert advisory.lang == "en", "an unverifiable translation must not ship"
    assert "500" not in advisory.body


def test_translation_repair_retry_can_succeed(payload, verdict):
    bad = translated_response(verdict)
    bad["actions"] = bad["actions"][:1]  # dropped actions
    provider = FakeProvider(
        [english_response(verdict), bad, translated_response(verdict)]
    )

    advisory = generate_advisory(
        payload, lang="sw", providers=[provider], use_cache=False
    )

    assert advisory.lang == "sw"
    assert len(provider.calls) == 3
    assert "rejected" in provider.calls[2]["user"]


def test_translated_advisory_uses_the_translated_heading(payload, verdict):
    provider = FakeProvider([english_response(verdict), translated_response(verdict)])
    advisory = generate_advisory(
        payload, lang="sw", providers=[provider], use_cache=False
    )

    expected = (strings_for("sw").get("ui_strings") or {}).get("what_to_do")
    assert expected, "sw must have a translated 'what to do' heading"
    assert expected in advisory.body
    assert "What to do:" not in advisory.body


# --------------------------------------------------------------------------- #
# check_translation
# --------------------------------------------------------------------------- #
def test_check_translation_accepts_a_faithful_translation(verdict):
    source = english_response(verdict)
    assert check_translation(translated_response(verdict), source, verdict) == []


def test_check_translation_rejects_dropped_actions(verdict):
    source = english_response(verdict)
    bad = translated_response(verdict)
    bad["actions"] = bad["actions"][:-1]
    assert check_translation(bad, source, verdict)


def test_check_translation_rejects_untranslated_passthrough(verdict):
    """Returning the input unchanged is a silent failure, not a translation."""
    source = english_response(verdict)
    assert check_translation(dict(source), source, verdict)


def test_check_translation_rejects_an_invented_figure(verdict):
    source = english_response(verdict)
    bad = translated_response(verdict)
    bad["body"] += " 777"
    errors = check_translation(bad, source, verdict)
    assert errors and any("777" in e for e in errors)


# --------------------------------------------------------------------------- #
# SMS translations
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("lang", ["en"] + TRANSLATABLE)
def test_sms_fits_one_segment_in_every_language(lang, rules):
    """Kiswahili and Kinyarwanda run longer than English -- the cap still holds."""
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        payload = PredictionPayload.from_dict(
            json.loads(path.read_text(encoding="utf-8"))
        )
        sms = render_sms(build_verdict(payload), rules, lang=lang)
        assert (
            len(sms) <= rules["delivery"]["sms_max_chars"]
        ), f"{lang}/{path.stem}: {len(sms)} chars -- {sms!r}"


@pytest.mark.parametrize("lang", TRANSLATABLE)
def test_sms_actually_uses_the_translation(lang, rules, payload):
    verdict = build_verdict(payload)
    translated = render_sms(verdict, rules, lang=lang)
    english = render_sms(verdict, rules, lang="en")
    assert translated != english, f"{lang} SMS is identical to English"


def test_unknown_language_falls_back_to_english(rules, payload):
    verdict = build_verdict(payload)
    assert render_sms(verdict, rules, lang="xx") == render_sms(
        verdict, rules, lang="en"
    )


def test_missing_string_falls_back_per_string(rules, payload, monkeypatch):
    """A partially translated language must still send a usable message."""
    monkeypatch.setattr(
        "src.advisory.rules.strings_for",
        lambda lang: {"band_labels": {}, "sms_actions": {}},
    )
    verdict = build_verdict(payload)
    sms = render_sms(verdict, rules, lang="sw")
    assert sms == render_sms(verdict, rules, lang="en")


# --------------------------------------------------------------------------- #
# The i18n config itself
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def i18n():
    return yaml.safe_load(I18N_PATH.read_text(encoding="utf-8"))


def test_every_configured_language_is_translated(i18n, rules):
    configured = {lang for lang in rules["delivery"]["languages"] if lang != "en"}
    assert configured <= set(i18n["languages"]), "a configured language has no strings"


@pytest.mark.parametrize("lang", TRANSLATABLE)
def test_no_string_is_missing_from_a_language(lang, i18n, rules):
    entry = i18n["languages"][lang]
    expected_bands = {b["id"] for b in rules["yield_bands"]} | {"unknown"}
    expected_actions = {r["id"] for r in rules["drivers"]} | {"all_clear"}

    assert expected_bands <= set(entry["band_labels"])
    assert expected_actions <= set(entry["sms_actions"])
    assert entry["ui_strings"].get("what_to_do")


@pytest.mark.parametrize("lang", TRANSLATABLE)
def test_translated_sms_actions_stay_short(lang, i18n):
    """A long translation reintroduces the truncation we just eliminated."""
    for key, value in i18n["languages"][lang]["sms_actions"].items():
        assert len(value) <= 100, f"{lang}.{key} is {len(value)} chars: {value!r}"


@pytest.mark.parametrize("lang", TRANSLATABLE)
def test_review_status_is_recorded(lang, i18n):
    """Not a gate -- the report must be able to state which languages a human checked."""
    entry = i18n["languages"][lang]
    assert entry["review_status"] in {"unreviewed", "reviewed"}
    if entry["review_status"] == "reviewed":
        assert entry["reviewed_by"].strip(), "a reviewed language needs a reviewer name"


def test_loader_tolerates_a_missing_file(tmp_path):
    assert load_i18n(str(tmp_path / "nope.yaml")) == {}
