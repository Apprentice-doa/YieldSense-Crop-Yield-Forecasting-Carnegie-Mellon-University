from __future__ import annotations
import json
import os
import uuid
from typing import Any
import redis
from sqlalchemy.orm import Session
from models.response import ChatResponse
from src.services.farmer_service import FarmerService
from src.services.summary_service import SYSTEM_PROMPT, _get_client, _get_deployment
from tools import browser, db as db_tools, weather as weather_tools

SESSION_TTL = int(os.getenv("CHAT_SESSION_TTL_SECONDS", 7200))  # 2 hours

_redis: redis.Redis | None = None

def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(
            os.environ["REDIS_URL"],
            decode_responses=True,
        )
    return _redis

def _farmer_key(farmer_id: int) -> str:
    return f"farmer:{farmer_id}"

def _session_key(session_id: str) -> str:
    return f"session:{session_id}:meta"

def _conv_key(session_id: str, conversation_id: str) -> str:
    return f"session:{session_id}:conv:{conversation_id}"

def _get_farmer_profile(farmer_id: int, db: Session) -> dict:
    r = _get_redis()
    key = _farmer_key(farmer_id)
    cached = r.get(key)
    if cached:
        return json.loads(cached)

    farmer = FarmerService(db).get_farmer(farmer_id)
    if not farmer:
        return {}

    profile = {
        "id": farmer.id,
        "name": farmer.name,
        "farm_country": farmer.farm_country,
        "farm_state_region": farmer.farm_state_region,
        "area_of_farmland": farmer.area_of_farmland,
        "crop_profiles": [
            {
                "crop_type": cp.crop_type,
                "planting_month": cp.planting_month,
                "harvest_month": cp.harvest_month,
                "average_yield_tons": cp.average_yield_tons,
            }
            for cp in (farmer.crop_profiles or [])
        ],
    }
    r.setex(key, SESSION_TTL, json.dumps(profile))
    return profile

def _get_or_create_session(session_id: str, farmer_id: int, language: str) -> dict:
    r = _get_redis()
    key = _session_key(session_id)
    raw = r.get(key)
    if raw:
        r.expire(key, SESSION_TTL)
        return json.loads(raw)

    meta = {
        "farmer_id": farmer_id,
        "language": language,
        "active_conversation_id": str(uuid.uuid4()),
    }
    r.setex(key, SESSION_TTL, json.dumps(meta))
    return meta

def _load_history(session_id: str, conversation_id: str) -> list[dict]:
    r = _get_redis()
    key = _conv_key(session_id, conversation_id)
    raw = r.get(key)
    return json.loads(raw) if raw else []

def _save_history(session_id: str, conversation_id: str, history: list[dict]) -> None:
    r = _get_redis()
    key = _conv_key(session_id, conversation_id)
    r.setex(key, SESSION_TTL, json.dumps(history))

def new_conversation(session_id: str) -> str:
    """Start a fresh conversation within an existing session. Returns new conversation_id."""
    r = _get_redis()
    key = _session_key(session_id)
    raw = r.get(key)
    if not raw:
        raise ValueError(f"Session {session_id!r} not found.")
    meta = json.loads(raw)
    meta["active_conversation_id"] = str(uuid.uuid4())
    r.setex(key, SESSION_TTL, json.dumps(meta))
    return meta["active_conversation_id"]

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_yield_analytics",
            "description": "Retrieve the farmer's yield history, summary statistics and chart data.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for market prices, news or agronomic advice.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather and 7-day forecast for the farmer's location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Location name e.g. Nairobi, Kenya"}
                },
                "required": ["location"],
            },
        },
    },
]

def _execute_tool(name: str, args: dict, farmer_id: int, db: Session) -> tuple[str, dict | None]:
    chart: dict[str, Any] | None = None
    if name == "get_yield_analytics":
        summary = db_tools.get_yield_summary(db, farmer_id)
        chart = db_tools.build_yield_chart(db, farmer_id)
        return json.dumps(summary), chart
    if name == "web_search":
        results = browser.search(args.get("query", ""), max_results=3)
        snippets = "\n".join(f"- {r['title']}: {r['snippet']}" for r in results)
        return snippets, chart
    if name == "get_weather":
        data = weather_tools.get_weather(args.get("location", ""))
        return json.dumps(data), chart
    return "", chart

def _build_system_prompt(profile: dict) -> str:
    if not profile:
        return SYSTEM_PROMPT

    crop_lines = "\n".join(
        f"  - {cp['crop_type']}: planted {cp['planting_month']}, harvest {cp['harvest_month']}, avg yield {cp['average_yield_tons']} tons"
        for cp in profile.get("crop_profiles", [])
    ) or "  - unknown"
    location = f"{profile.get('farm_state_region')}, {profile.get('farm_country')}"
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"--- FARMER PROFILE ---\n"
        f"Name      : {profile.get('name')}\n"
        f"Location  : {location}\n"
        f"Farm size : {profile.get('area_of_farmland')} ha\n"
        f"Crops     :\n{crop_lines}\n"
        f"----------------------\n"
        f"Always address the farmer by name. Use the crop planting and harvest months above "
        f"to give season-aware advice. Only share this farmer's own data.\n\n"
        f"RESPONSE FORMAT: 2-3 sentences only. Stop after the 3rd sentence."
    )

def chat(
    session_id: str,
    farmer_id: int,
    user_message: str,
    db: Session,
    conversation_id: str | None = None,
) -> ChatResponse:
    """Process one farmer message and return a structured ChatResponse.

    - Detects language from the message; falls back to session language.
    - Injects farmer profile as system context (cached in Redis).
    - Runs analytics / web-search tools when the message warrants it.
    - Persists conversation history in Redis with a 2-hour inactivity TTL.
    """
    meta = _get_or_create_session(session_id, farmer_id, "en")
    conv_id = conversation_id or meta["active_conversation_id"]
    profile = _get_farmer_profile(farmer_id, db)
    system_prompt = _build_system_prompt(profile)
    history = _load_history(session_id, conv_id)
    history.append({"role": "user", "content": user_message})
    messages = [{"role": "system", "content": system_prompt}] + history

    chart: dict[str, Any] | None = None
    tools_called: list[str] = []
    # Agentic loop — LLM reasons and calls tools until it produces a final reply
    for _ in range(10):  # max 10 iterations to prevent infinite loops
        response = _get_client().chat.completions.create(
            model=_get_deployment(),
            messages=messages,
            tools=_TOOLS,
            tool_choice="auto",
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            break

        messages.append(msg)
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            tools_called.append(f"{tc.function.name}({args})")
            result, tool_chart = _execute_tool(tc.function.name, args, farmer_id, db)
            print(f"[tool result] {tc.function.name} -> {result[:200]}")
            chart = tool_chart or chart
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    print(f"[tools called] {tools_called}")

    assistant_reply = msg.content.strip()
    message_id = str(uuid.uuid4())
    history.append({"role": "assistant", "content": assistant_reply, "message_id": message_id})
    _save_history(session_id, conv_id, history)

    return ChatResponse(
        message=assistant_reply,
        language=meta["language"],
        session_id=session_id,
        conversation_id=conv_id,
        message_id=message_id,
        chart=chart,
    )
