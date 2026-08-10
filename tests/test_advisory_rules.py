"""Tests for the deterministic advisory rules engine.

The engine is the safety mechanism for the whole GenAI Advisory track: if it is
correct and the LLM is confined to rephrasing it, a farmer cannot receive an
invented yield figure or invented agronomic advice. These tests are what make
that claim true, so they assert the guarantees, not just the happy path.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from src.advisory.rules import (
    build_verdict,
    load_config,
    render_rules_advisory,
    render_sms,
)
from src.advisory.schemas import PredictionPayload

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "advisory"
FIXTURES = sorted(FIXTURE_DIR.glob("*.json"))


@pytest.fixture(scope="module")
def config():
    return load_config()


@pytest.fixture(scope="module")
def rules(config):
    return config[0]


def load_payload(path: Path) -> PredictionPayload:
    return PredictionPayload.from_dict(json.loads(path.read_text(encoding="utf-8")))


def ids(paths):
    return [p.stem for p in paths]


# --------------------------------------------------------------------------- #
# Every fixture must produce a usable advisory
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", FIXTURES, ids=ids(FIXTURES))
def test_every_fixture_produces_an_advisory(path, config, rules):
    verdict = build_verdict(load_payload(path), config)
    advisory = render_rules_advisory(verdict, rules)

    assert advisory.headline.strip()
    assert advisory.body.strip()
    assert verdict.actions, "every advisory must give the farmer something to do"
    assert advisory.disclaimer == rules["safety"]["disclaimer"]
    assert verdict.rules_version == rules["rules_version"]


@pytest.mark.parametrize("path", FIXTURES, ids=ids(FIXTURES))
def test_sms_fits_one_segment(path, config, rules):
    verdict = build_verdict(load_payload(path), config)
    sms = render_sms(verdict, rules)
    limit = rules["delivery"]["sms_max_chars"]
    assert 0 < len(sms) <= limit, f"SMS is {len(sms)} chars (limit {limit}): {sms!r}"


@pytest.mark.parametrize("path", FIXTURES, ids=ids(FIXTURES))
def test_sms_never_ends_mid_word(path, config, rules):
    sms = render_sms(build_verdict(load_payload(path), config), rules)
    assert not re.search(r"[a-z]{2}\.$", sms) or sms.rstrip(".").split()[-1] in {
        w.rstrip(".,;:") for w in sms.split()
    }
    assert "  " not in sms


@pytest.mark.parametrize("path", FIXTURES, ids=ids(FIXTURES))
def test_no_contradictory_water_advice(path, config):
    """A farmer must never be told to irrigate and to hold off in one advisory."""
    verdict = build_verdict(load_payload(path), config)
    fired = {a.rule_id for a in verdict.actions}
    assert not ({"rainfall_low", "soil_moisture_high"} <= fired)
    assert not ({"rainfall_high", "soil_moisture_low"} <= fired)
    assert not ({"soil_moisture_low", "soil_moisture_high"} <= fired)
    assert not ({"heat_stress", "cold_stress"} <= fired)


def test_conflict_keeps_the_field_measurement_over_the_catchment_signal(config):
    """Low rainfall + wet soil: trust the soil probe, not the rain gauge."""
    verdict = build_verdict(load_payload(FIXTURE_DIR / "edge_no_area.json"), config)
    fired = {a.rule_id for a in verdict.actions}
    assert "soil_moisture_high" in fired
    assert "rainfall_low" in verdict.suppressed_rules
    assert not any("irrigation for this field" in a.action for a in verdict.actions)


@pytest.mark.parametrize("path", FIXTURES, ids=ids(FIXTURES))
def test_verdict_is_deterministic(path, config):
    payload = load_payload(path)
    assert (
        build_verdict(payload, config).to_dict()
        == build_verdict(payload, config).to_dict()
    )


# --------------------------------------------------------------------------- #
# Numeric fidelity -- the guard that stops invented figures
# --------------------------------------------------------------------------- #
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


@pytest.mark.parametrize("path", FIXTURES, ids=ids(FIXTURES))
def test_rendered_text_states_no_number_outside_the_verdict(path, config, rules):
    """Every figure in the prose must trace back to Verdict.numeric_facts().

    The same assertion runs against LLM output in the eval harness (D5-D6). If it
    holds for the rules renderer, the check itself is trustworthy.
    """
    verdict = build_verdict(load_payload(path), config)
    advisory = render_rules_advisory(verdict, rules)

    allowed = set()
    for value in verdict.numeric_facts():
        allowed.add(f"{value:g}")
        allowed.add(f"{round(value):g}")
        allowed.add(f"{value:.0%}".rstrip("%"))

    # Prose is checked; the fixed disclaimer and static action copy are not
    # generated per-field, so numbers there are reviewed by hand instead.
    prose = f"{advisory.headline}\n" + "\n".join(
        line
        for line in advisory.body.splitlines()
        if not line.startswith("- ") or "typical" in line
    )
    # Identifiers carry digits ("Field_1") that are not claims about the crop.
    prose = prose.replace(verdict.field_id, "<field>")

    for token in NUMBER_RE.findall(prose):
        assert token in allowed, (
            f"{path.name}: number {token!r} appears in the advisory but is not a "
            f"verdict fact. Allowed: {sorted(allowed)}\nProse: {prose!r}"
        )


# --------------------------------------------------------------------------- #
# Band classification
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "fixture_name,expected_band",
    [
        ("band_critical", "critical"),
        ("band_below", "below"),
        ("band_on_track", "on_track"),
        ("band_above", "above"),
    ],
)
def test_bands_classify_as_labelled(fixture_name, expected_band, config):
    verdict = build_verdict(load_payload(FIXTURE_DIR / f"{fixture_name}.json"), config)
    assert verdict.band == expected_band


def test_unknown_crop_degrades_instead_of_guessing(config):
    verdict = build_verdict(
        load_payload(FIXTURE_DIR / "edge_unknown_crop.json"), config
    )
    assert verdict.band == "unknown"
    assert verdict.baseline_yield is None
    assert verdict.baseline_ratio is None
    assert verdict.actions, "an unknown crop still deserves post-harvest guidance"
    # Volume-derived drying time is unknowable without a band, so it is omitted.
    assert verdict.post_harvest.drying_days is None


@pytest.mark.parametrize("path", FIXTURES, ids=ids(FIXTURES))
def test_no_placeholder_leaks_into_farmer_facing_text(path, config, rules):
    """Regression: an unset drying_days once rendered as 'roughly None drying days'."""
    advisory = render_rules_advisory(build_verdict(load_payload(path), config), rules)
    text = f"{advisory.headline}\n{advisory.body}\n{advisory.sms_text}"
    for placeholder in ("None", "null", "nan", "{", "}"):
        assert (
            placeholder not in text
        ), f"{path.name}: leaked {placeholder!r} in {text!r}"


# --------------------------------------------------------------------------- #
# Data quality -- rules must be suppressed, not fired on garbage
# --------------------------------------------------------------------------- #
def test_invalid_ndvi_suppresses_vegetation_rules(config):
    verdict = build_verdict(
        load_payload(FIXTURE_DIR / "edge_invalid_ndvi.json"), config
    )
    assert any(f.startswith("NDVI:") for f in verdict.data_quality_flags)
    assert "ndvi_low" in verdict.suppressed_rules
    assert "ndvi_high" in verdict.suppressed_rules
    fired = {a.rule_id for a in verdict.actions}
    assert not (fired & {"ndvi_low", "ndvi_high"})


def test_missing_weather_suppresses_weather_rules(config):
    verdict = build_verdict(
        load_payload(FIXTURE_DIR / "edge_missing_weather.json"), config
    )
    fired = {a.rule_id for a in verdict.actions}
    assert not (fired & {"rainfall_low", "rainfall_high", "heat_stress", "cold_stress"})
    for rule_id in ("rainfall_low", "soil_moisture_low", "heat_stress"):
        assert rule_id in verdict.suppressed_rules


def test_heat_stress_fires_on_absolute_threshold(config):
    verdict = build_verdict(load_payload(FIXTURE_DIR / "edge_heat_stress.json"), config)
    assert "heat_stress" in {a.rule_id for a in verdict.actions}


# --------------------------------------------------------------------------- #
# Post-harvest quantities are never invented
# --------------------------------------------------------------------------- #
def test_no_area_means_no_invented_quantities(config):
    verdict = build_verdict(load_payload(FIXTURE_DIR / "edge_no_area.json"), config)
    ph = verdict.post_harvest
    assert ph is not None
    assert ph.market_note, "qualitative guidance still applies without an area"
    assert ph.expected_volume is None
    assert ph.storage_capacity_needed is None
    assert ph.labour_days is None


def test_area_drives_post_harvest_quantities(config, rules):
    verdict = build_verdict(load_payload(FIXTURE_DIR / "band_on_track.json"), config)
    ph = verdict.post_harvest
    assert ph.expected_volume == pytest.approx(verdict.predicted_yield * 1.5, rel=1e-3)
    assert ph.storage_capacity_needed > ph.expected_volume
    # Labour-days are reported to one decimal: a farmer plans in half-days.
    assert ph.labour_days == round(1.5 * rules["post_harvest"]["labour_days_per_ha"], 1)
    assert ph.drying_days == rules["post_harvest"]["drying_days_per_band"]["on_track"]


# --------------------------------------------------------------------------- #
# Confidence
# --------------------------------------------------------------------------- #
def test_wide_interval_is_low_confidence_and_says_so(config):
    verdict = build_verdict(
        load_payload(FIXTURE_DIR / "edge_wide_interval.json"), config
    )
    assert verdict.confidence == "low"
    assert any("rough guide" in d for d in verdict.drivers)


def test_tight_interval_is_high_confidence(config):
    verdict = build_verdict(load_payload(FIXTURE_DIR / "band_on_track.json"), config)
    assert verdict.confidence == "high"


# --------------------------------------------------------------------------- #
# Action budget and ordering
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", FIXTURES, ids=ids(FIXTURES))
def test_actions_respect_budget_and_urgency_order(path, config, rules):
    verdict = build_verdict(load_payload(path), config)
    in_season = [a for a in verdict.actions if a.stage == "in_season"]
    assert len(in_season) <= rules["delivery"]["max_actions_in_full"]

    order = {"immediate": 0, "soon": 1, "routine": 2}
    ranks = [order[a.urgency] for a in in_season]
    assert ranks == sorted(ranks), "urgent actions must come first"


# --------------------------------------------------------------------------- #
# Config integrity -- these configs are the contract, so guard them
# --------------------------------------------------------------------------- #
def test_baseline_caveat_is_carried_into_every_verdict(config):
    verdict = build_verdict(load_payload(FIXTURE_DIR / "band_above.json"), config)
    assert "NOT a multi-year" in verdict.baseline_caveat


def test_no_driver_rule_references_a_missing_percentile(config):
    rules, baselines = config
    for rule in rules["drivers"]:
        if "absolute" in rule:
            continue
        feature = baselines["features"].get(rule["feature"])
        assert feature is not None, f"{rule['id']}: no baseline for {rule['feature']}"
        assert rule["percentile"] in feature, (
            f"{rule['id']}: percentile {rule['percentile']} missing for "
            f"{rule['feature']}"
        )


def test_every_band_has_a_market_note(config):
    rules, _ = config
    notes = rules["post_harvest"]["market_note_by_band"]
    for band in rules["yield_bands"]:
        assert band["id"] in notes, f"band {band['id']} has no post-harvest note"


def test_safety_config_is_present_and_non_empty():
    rules = yaml.safe_load(
        (REPO_ROOT / "configs" / "advisory_rules.yaml").read_text(encoding="utf-8")
    )
    assert rules["safety"]["disclaimer"].strip()
    assert len(rules["safety"]["banned_topics"]) >= 5
