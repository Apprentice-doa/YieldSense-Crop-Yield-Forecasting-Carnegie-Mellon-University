"""The D5-D6 quality gates, run as tests.

`scripts/advisory_eval.py` is the human-facing report; this is the same set of
gates wired into CI so a regression fails a build instead of waiting to be
noticed in a demo. Runs entirely on the rules path -- no API key, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.advisory.generator import generate_advisory
from src.advisory.rules import build_verdict, load_config
from src.advisory.schemas import PredictionPayload
from src.advisory.validation import (
    check_band_consistency,
    check_numeric_fidelity,
    check_safety,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN = REPO_ROOT / "tests" / "fixtures" / "golden" / "golden_set.json"

DOC = json.loads(GOLDEN.read_text(encoding="utf-8"))
ITEMS = DOC["items"]
IDS = [item["id"] for item in ITEMS]


@pytest.fixture(scope="module")
def rules():
    return load_config()[0]


def advisory_for(item):
    payload = PredictionPayload.from_dict(item["payload"])
    # providers=[] forces the offline rules path: CI must never call an API.
    return payload, generate_advisory(payload, providers=[], use_cache=False)


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_schema_validity(item):
    _, advisory = advisory_for(item)
    for field_name in ("headline", "body", "sms_text", "disclaimer"):
        assert getattr(advisory, field_name).strip(), f"{field_name} is empty"


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_numeric_fidelity(item):
    payload, advisory = advisory_for(item)
    verdict = build_verdict(payload)
    prose = "\n".join(
        line for line in advisory.body.splitlines() if not line.startswith("- ")
    )
    errors = check_numeric_fidelity(f"{advisory.headline}\n{prose}", verdict)
    assert not errors, errors


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_safety(item, rules):
    _, advisory = advisory_for(item)
    errors = check_safety(f"{advisory.headline}\n{advisory.body}", rules)
    assert not errors, errors


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_band_consistency(item):
    payload, advisory = advisory_for(item)
    verdict = build_verdict(payload)
    errors = check_band_consistency(
        {"headline": advisory.headline, "body": advisory.body}, verdict
    )
    assert not errors, errors


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_sms_is_one_segment_with_the_instruction_intact(item, rules):
    payload, advisory = advisory_for(item)
    verdict = build_verdict(payload)

    assert len(advisory.sms_text) <= rules["delivery"]["sms_max_chars"]

    in_season = [a for a in verdict.actions if a.stage == "in_season"]
    top = in_season[0] if in_season else verdict.actions[0]
    expected = top.sms_action or top.action
    assert expected in advisory.sms_text


# --------------------------------------------------------------------------- #
# Properties of the set itself
# --------------------------------------------------------------------------- #
def test_every_band_is_represented():
    """Uniform sampling would give us ~0 critical cases; stratification must hold."""
    strata = {item["stratum"] for item in ITEMS}
    assert {"critical", "below", "on_track", "above", "edge"} <= strata


def test_critical_band_is_over_sampled():
    """`critical` is 1% of real rows and is the copy that matters most."""
    critical = [i for i in ITEMS if i["stratum"] == "critical"]
    assert len(critical) >= 5


def test_every_driver_rule_is_exercised_by_the_set(rules):
    """A rule no golden-set case triggers is a rule nobody is reviewing."""
    fired = set()
    for item in ITEMS:
        payload = PredictionPayload.from_dict(item["payload"])
        fired |= {a.rule_id for a in build_verdict(payload).actions}

    expected = {r["id"] for r in rules["drivers"]} | {"all_clear"}
    missing = expected - fired
    assert not missing, f"golden set never exercises: {sorted(missing)}"


def test_synthetic_inputs_are_declared():
    """Nobody should read a confidence metric off this set and think it measured."""
    assert all(item["interval_is_synthetic"] for item in ITEMS)
    assert "synthetic" in DOC["_caveat"]
