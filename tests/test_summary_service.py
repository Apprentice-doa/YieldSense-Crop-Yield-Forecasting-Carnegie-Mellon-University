from unittest.mock import MagicMock, patch
from models.request import YieldPredictionContext
from src.services.summary_service import get_summary

CTX = YieldPredictionContext(
    farmer_name="John Doe",
    crop_type="Maize",
    farm_location="Nairobi, Kenya",
    season="Long Rains 2025",
    harvest_date="August 2025",
    predicted_yield_kg_per_ha=3500.0,
    farm_size_ha=2.0,
    soil_type="Loam",
    irrigation_method="Drip",
)


def _mock_response(content: str):
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    client = MagicMock()
    client.chat.completions.create.return_value = response
    return client


@patch("src.summary_service._get_client")
def test_get_summary_returns_llm_content(mock_get_client):
    mock_get_client.return_value = _mock_response("Your maize yield looks promising, John Doe!")

    result = get_summary(CTX)

    assert result == "Your maize yield looks promising, John Doe!"


@patch("src.summary_service._get_client")
def test_get_summary_sends_correct_messages(mock_get_client):
    mock_get_client.return_value = _mock_response("ok")

    get_summary(CTX)

    call_kwargs = mock_get_client.return_value.chat.completions.create.call_args
    messages = call_kwargs.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "John Doe" in messages[1]["content"]
    assert "Maize" in messages[1]["content"]


@patch("src.summary_service._get_client")
def test_get_summary_yield_category_moderate(mock_get_client):
    mock_get_client.return_value = _mock_response("moderate advice")

    result = get_summary(CTX)  # 3500 kg/ha → moderate

    assert CTX.yield_category == "moderate"
    assert result == "moderate advice"


@patch("src.summary_service._get_client")
def test_get_summary_high_yield(mock_get_client):
    ctx = YieldPredictionContext(
        farmer_name="Jane",
        crop_type="Rice",
        farm_location="Kampala",
        season="Dry 2025",
        harvest_date="Dec 2025",
        predicted_yield_kg_per_ha=5000.0,
        farm_size_ha=1.0,
    )
    mock_get_client.return_value = _mock_response("high yield advice")

    result = get_summary(ctx)

    assert ctx.yield_category == "high"
    assert result == "high yield advice"


@patch("src.summary_service._get_client")
def test_get_summary_optional_fields_absent(mock_get_client):
    ctx = YieldPredictionContext(
        farmer_name="Ali",
        crop_type="Sorghum",
        farm_location="Kigali",
        season="Season A",
        harvest_date="June 2025",
        predicted_yield_kg_per_ha=1500.0,
        farm_size_ha=0.5,
    )
    mock_get_client.return_value = _mock_response("low yield advice")

    result = get_summary(ctx)

    assert result == "low yield advice"
    prompt = mock_get_client.return_value.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "Soil type" not in prompt
    assert "Irrigation method" not in prompt
