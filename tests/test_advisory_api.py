"""Tests for the advisory HTTP layer.

Skipped entirely when FastAPI is absent. That is deliberate: `src/advisory/`
must stay importable and testable without a web framework, so the API tests are
the only ones allowed to require one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="FastAPI not installed")
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.advisory.api import router  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "advisory"


@pytest.fixture(scope="module")
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def forecast():
    return json.loads((FIXTURE_DIR / "band_critical.json").read_text(encoding="utf-8"))


def test_advisory_endpoint_returns_a_usable_advisory(client, forecast):
    """With no API key configured this exercises the rules fallback path."""
    resp = client.post("/api/v1/advisory", json=forecast)
    assert resp.status_code == 200

    body = resp.json()
    assert body["field_id"] == forecast["field_id"]
    assert body["headline"] and body["body"] and body["sms_text"]
    assert body["disclaimer"]
    assert body["generated_by"] in {"rules", "llm", "llm_fallback_rules"}
    assert body["verdict"]["band"] == "critical"


def test_sms_endpoint_never_exceeds_one_segment(client, forecast):
    resp = client.post("/api/v1/advisory/sms", json=forecast)
    assert resp.status_code == 200

    body = resp.json()
    assert body["characters"] == len(body["sms_text"])
    assert body["characters"] <= 160


def test_health_reports_provider_and_rules_state(client):
    resp = client.get("/api/v1/advisory/health")
    assert resp.status_code == 200

    body = resp.json()
    assert body["status"] == "healthy"
    assert body["rules_version"]
    assert {p["name"] for p in body["providers"]} == {"gemini", "openai"}
    assert "degraded_to_rules_only" in body


def test_missing_required_field_is_rejected(client):
    resp = client.post("/api/v1/advisory", json={"field_id": "F1"})
    assert resp.status_code == 422


def test_unknown_crop_still_returns_200(client, forecast):
    """An unmodelled crop degrades to guidance, it does not error."""
    forecast["crop_type"] = "Teff"
    resp = client.post("/api/v1/advisory", json=forecast)
    assert resp.status_code == 200
    assert resp.json()["verdict"]["band"] == "unknown"
