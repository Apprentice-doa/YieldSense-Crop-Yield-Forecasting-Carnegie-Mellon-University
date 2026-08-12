

SYSTEM_PROMPT = (
    "You are YieldSenseAI, an expert agricultural intelligence assistant developed to help "
    "smallholder and commercial farmers understand their crop yield forecasts and take "
    "actionable steps to maximise their harvest outcomes. "
    "You communicate in a clear, encouraging, and practical tone — avoiding jargon. "
    "Always ground your advice in the specific crop, season, location, and yield data provided. "
    "Never fabricate statistics. If data is insufficient, ask a clarifying question."
)


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
