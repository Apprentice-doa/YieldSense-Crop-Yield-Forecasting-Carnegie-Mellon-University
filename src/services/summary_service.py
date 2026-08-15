import os
from typing import Optional
from openai import AzureOpenAI
from models.request import YieldPredictionContext

_client: Optional[AzureOpenAI] = None

def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "https://mcochiengai.services.ai.azure.com/openai/v1")
        base = endpoint.split("/openai")[0]
        _client = AzureOpenAI(
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
            azure_endpoint=base,
            api_version="2025-01-01-preview",
        )
    return _client

def _get_deployment() -> str:
    return os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.2")

SYSTEM_PROMPT = """You are YieldSense, an agricultural intelligence assistant helping smallholder farmers
in Africa understand their crop yield forecasts and make better post-harvest decisions.

Scope: Only answer questions related to agriculture, farming, crop yields, weather, market prices,
storage, and soil health. Politely decline anything outside this scope.

Reasoning: Before responding, think step by step:
1. What is the farmer actually asking?
2. What data do I already have from their profile?
3. What tools do I need to call to get missing information?
4. After getting tool results, do I need more information or can I now give a complete answer?
Call tools as many times as needed until you have enough to give a fully grounded response.

Tone: Clear, encouraging, practical. No jargon.
RESPOND IN EXACTLY 2-3 SENTENCES. No more. Never exceed 3 sentences under any circumstances.
No bullet points, no bold, no markdown. Never ask for photos or files.

Data: Always ground advice in the farmer's specific crop, season, location, and yield data.
Never fabricate statistics or benchmarks. If data is insufficient, ask a clarifying question.

Tools:
- get_yield_analytics: use when farmer asks about their yield history or past performance
- get_weather: use for any question involving current conditions, rainfall or forecast
- web_search: use for market prices, news or agronomic best practices

Safety: Always remind farmers that AI advice is a guide, not a substitute for local agricultural
extension officers or agronomists when making significant financial or planting decisions.

Language: Detect the language of the farmer's message and respond in that same language.
Supported languages: English, Swahili, Kinyarwanda, French, Amharic, Luganda."""

def build_summary_prompt(ctx: YieldPredictionContext) -> str:
    soil_line = f"Soil type        : {ctx.soil_type}" if ctx.soil_type else ""
    irrigation_line = f"Irrigation method: {ctx.irrigation_method}" if ctx.irrigation_method else ""

    return f"""
      A crop yield prediction has just been completed for the following farmer.
      Please generate a structured summary and harvest preparation guide.

      --- FARMER & FARM DETAILS ---
      Farmer name   : {ctx.farmer_name}
      Location      : {ctx.farm_location}
      Farm size     : {ctx.farm_size_ha} hectares
      {soil_line}
      {irrigation_line}

      --- PREDICTION RESULTS ---
      Crop                  : {ctx.crop_type}
      Season                : {ctx.season}
      Expected harvest date : {ctx.harvest_date}
      Predicted yield       : {ctx.predicted_yield_kg_per_ha:.0f} kg/ha  ({ctx.total_yield_kg:,.0f} kg total)
      Yield category        : {ctx.yield_category.upper()}

      --- YOUR RESPONSE MUST INCLUDE ---
      1. Yield Summary
         - Interpret what this yield means for {ctx.farmer_name} in plain language.
         - Compare it to typical benchmarks for {ctx.crop_type} in {ctx.farm_location}.
         - Flag any risks associated with a {ctx.yield_category} yield.

      2. Harvest Preparation Checklist (specific to {ctx.harvest_date})
         - Key tasks to complete 4-6 weeks before harvest.
         - Equipment and storage requirements based on {ctx.total_yield_kg:,.0f} kg total yield.
         - Labour and logistics recommendations.

      3. Post-Harvest Advice
         - Storage best practices for {ctx.crop_type}.
         - Market timing suggestions given the {ctx.season} season.
         - Soil recovery steps to prepare for the next planting cycle.

      4. One-Line Motivational Closing
         - End with a single encouraging sentence addressed to {ctx.farmer_name}.
      """.strip()

def build_prompt(ctx: YieldPredictionContext) -> str:
    """Return the full one-shot prompt to send to the LLM."""
    return f"{SYSTEM_PROMPT}\n\n{build_summary_prompt(ctx)}"

def get_summary(ctx: YieldPredictionContext) -> str:
    response = _get_client().chat.completions.create(
        model=_get_deployment(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_summary_prompt(ctx)},
        ],
    )
    return response.choices[0].message.content

