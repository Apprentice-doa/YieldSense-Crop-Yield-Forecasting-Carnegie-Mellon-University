"""
Live integration test — calls the real Azure OpenAI endpoint.

Requires AZURE_OPENAI_API_KEY to be set in .env (or the environment).
Skip automatically when the key is absent.
"""
import os
import pytest
import src.summary_service as svc
from dotenv import load_dotenv

load_dotenv()
svc._client = None  # force lazy re-init after load_dotenv

pytestmark = pytest.mark.skipif(
    not os.environ.get("AZURE_OPENAI_API_KEY")
    or os.environ.get("AZURE_OPENAI_API_KEY") == "your_azure_key_here",
    reason="AZURE_OPENAI_API_KEY not configured",
)

from models.request import YieldPredictionContext  # noqa: E402
from src.summary_service import get_summary  # noqa: E402

CTX = YieldPredictionContext(
    farmer_name="Amara Diallo",
    crop_type="Maize",
    farm_location="Nairobi, Kenya",
    season="Long Rains 2025",
    harvest_date="August 2025",
    predicted_yield_kg_per_ha=3200.0,
    farm_size_ha=2.5,
    soil_type="Loam",
    irrigation_method="Drip",
)


def test_live_get_summary_returns_text():
    result = get_summary(CTX)
    assert isinstance(result, str)
    assert len(result) > 100


def test_live_get_summary_mentions_farmer_name():
    result = get_summary(CTX)
    assert "Amara" in result


def test_live_get_summary_covers_required_sections():
    result = get_summary(CTX)
    lower = result.lower()
    assert any(w in lower for w in ["yield", "harvest", "storage", "market"])
