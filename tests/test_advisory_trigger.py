"""Tests for the on-prediction-complete trigger."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.advisory import trigger
from src.advisory.trigger import clear_sinks, on_prediction_complete, register_sink

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "advisory"


@pytest.fixture(autouse=True)
def clean_state():
    clear_sinks()
    trigger._cache.clear()
    yield
    clear_sinks()


@pytest.fixture
def forecast():
    return json.loads((FIXTURE_DIR / "band_below.json").read_text(encoding="utf-8"))


def test_trigger_returns_an_advisory(forecast):
    advisory = on_prediction_complete(forecast)
    assert advisory.field_id == forecast["field_id"]
    assert advisory.headline and advisory.sms_text


def test_every_registered_sink_receives_the_advisory(forecast):
    received = []
    register_sink(lambda a: received.append(("db", a.field_id)))
    register_sink(lambda a: received.append(("sms", a.field_id)))

    on_prediction_complete(forecast)

    assert {r[0] for r in received} == {"db", "sms"}


def test_a_failing_sink_does_not_stop_the_others(forecast):
    delivered = []

    def broken(_advisory):
        raise RuntimeError("database is down")

    register_sink(broken)
    register_sink(lambda a: delivered.append(a.field_id))

    advisory = on_prediction_complete(forecast)

    assert delivered == [
        forecast["field_id"]
    ], "a broken sink must not lose the advisory"
    assert advisory.field_id == forecast["field_id"]


def test_registering_the_same_sink_twice_delivers_once(forecast):
    calls = []

    def sink(advisory):
        calls.append(advisory.field_id)

    register_sink(sink)
    register_sink(sink)
    on_prediction_complete(forecast)

    assert len(calls) == 1


def test_revised_forecast_regenerates_rather_than_serving_stale_advice(forecast):
    first = on_prediction_complete(forecast)

    revised = dict(forecast)
    revised["predicted_yield"] = forecast["predicted_yield"] * 0.5
    second = on_prediction_complete(revised)

    assert second.verdict.predicted_yield != first.verdict.predicted_yield
    assert second.verdict.band != first.verdict.band
