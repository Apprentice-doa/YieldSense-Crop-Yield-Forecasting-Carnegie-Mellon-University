"""Provider abstraction for advisory generation.

Deliberately thin. The generator owns retries, validation and fallback; a
provider's only job is "given a system prompt and a user prompt, return parsed
JSON or raise". That keeps vendor differences in one small place and makes the
whole generation path testable with FakeProvider, no network and no API key.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class LLMError(RuntimeError):
    """Provider failed in a way the generator should handle (retry or fall back)."""

    def __init__(
        self, message: str, *, retryable: bool = False, status: Optional[int] = None
    ):
        super().__init__(message)
        self.retryable = retryable
        self.status = status


class LLMProvider(ABC):
    """One remote model, wrapped."""

    name: str = "base"
    model: str = ""

    @abstractmethod
    def generate_json(self, system: str, user: str) -> Dict[str, Any]:
        """Return the model's response parsed as a JSON object.

        Raises LLMError on transport failure, auth failure, or unparseable output.
        """

    # -- shared helpers ----------------------------------------------------- #
    @staticmethod
    def parse_json_payload(text: str) -> Dict[str, Any]:
        """Parse a JSON object out of a model response.

        Models wrap JSON in ```json fences often enough that failing on it would
        cost us a retry for no reason, so we strip fences before parsing. We do
        NOT attempt to repair malformed JSON -- that is what the repair retry is
        for, and silently patching output would defeat the point of validating.
        """
        if not text or not text.strip():
            raise LLMError("empty response from provider")

        cleaned = text.strip()
        fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
        if fence:
            cleaned = fence.group(1).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMError(f"response was not valid JSON: {exc}") from exc

        if not isinstance(parsed, dict):
            raise LLMError(f"expected a JSON object, got {type(parsed).__name__}")
        return parsed


class FakeProvider(LLMProvider):
    """Scripted provider for tests.

    Takes a list of responses (dicts to return, or Exceptions to raise) and plays
    them in order, so a test can stage "fails, then returns bad output, then
    succeeds" without touching the network.
    """

    name = "fake"

    def __init__(self, responses: List[Any], model: str = "fake-1"):
        self.responses = list(responses)
        self.model = model
        self.calls: List[Dict[str, str]] = []

    def generate_json(self, system: str, user: str) -> Dict[str, Any]:
        self.calls.append({"system": system, "user": user})
        if not self.responses:
            raise LLMError("FakeProvider ran out of scripted responses")
        nxt = self.responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        if isinstance(nxt, str):
            return self.parse_json_payload(nxt)
        return nxt
