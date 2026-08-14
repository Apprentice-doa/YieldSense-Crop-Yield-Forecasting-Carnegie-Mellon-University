from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatResponse:
    message: str                        # AI reply in the farmer's language
    language: str                       # ISO 639-1 code used
    session_id: str
    conversation_id: str
    message_id: str
    chart: dict[str, Any] | None = None  # Plotly JSON — present when analytics ran
