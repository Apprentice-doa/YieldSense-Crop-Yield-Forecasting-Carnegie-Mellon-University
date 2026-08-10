"""Gemini and OpenAI adapters over plain HTTP.

We call the REST APIs with `requests` rather than the vendor SDKs. Two reasons:
`requests` is already a project dependency so this adds none, and retry, timeout
and error classification stay in our hands instead of varying by SDK version.

Both providers are asked for JSON directly (Gemini: responseMimeType, OpenAI:
response_format), but the generator still validates the result -- a provider
promising JSON is not the same as the content being correct.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests

from .base import LLMError, LLMProvider

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _api_key(env_var: str, provider: str) -> str:
    key = os.environ.get(env_var, "").strip()
    if not key:
        raise LLMError(f"{provider}: {env_var} is not set", retryable=False)
    return key


def _classify(status: int, body: str, provider: str) -> LLMError:
    return LLMError(
        f"{provider} returned HTTP {status}: {body[:300]}",
        retryable=status in RETRYABLE_STATUS,
        status=status,
    )


class GeminiProvider(LLMProvider):
    """Google Gemini via generativelanguage REST."""

    name = "gemini"

    def __init__(self, config: Dict[str, Any], generation: Dict[str, Any]):
        self.model = config["model"]
        self.endpoint = config["endpoint"].format(model=self.model)
        self.api_key_env = config.get("api_key_env", "GEMINI_API_KEY")
        self.timeout = config.get("timeout_seconds", 20)
        self.generation = generation

    def generate_json(self, system: str, user: str) -> Dict[str, Any]:
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": self.generation.get("temperature", 0.3),
                "maxOutputTokens": self.generation.get("max_output_tokens", 800),
                "responseMimeType": "application/json",
            },
        }
        try:
            resp = requests.post(
                self.endpoint,
                headers={"x-goog-api-key": _api_key(self.api_key_env, self.name)},
                json=payload,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise LLMError(f"{self.name}: request timed out", retryable=True) from exc
        except requests.RequestException as exc:
            raise LLMError(f"{self.name}: {exc}", retryable=True) from exc

        if resp.status_code != 200:
            raise _classify(resp.status_code, resp.text, self.name)

        try:
            candidates = resp.json()["candidates"]
            text = candidates[0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, ValueError) as exc:
            # A blocked or truncated response lands here; treat as retryable so
            # the generator can try the fallback provider before giving up.
            raise LLMError(
                f"{self.name}: unexpected response shape ({exc})", retryable=True
            ) from exc

        return self.parse_json_payload(text)


class OpenAIProvider(LLMProvider):
    """OpenAI chat completions, and any endpoint that speaks the same protocol.

    Azure AI Foundry's `/openai/v1` route is OpenAI-compatible down to Bearer
    auth, so it reuses this class. Two things do vary between deployments and
    are therefore config, not constants:

    - the token limit parameter (`max_tokens` on older models,
      `max_completion_tokens` on newer ones, which reject the old name outright)
    - whether `temperature` is accepted at all

    Endpoint and model can come from environment variables so that a tenant's
    resource name and deployment name never land in a committed file.
    """

    name = "openai"

    def __init__(self, config: Dict[str, Any], generation: Dict[str, Any]):
        self.name = config.get("name", "openai")
        self.model = os.environ.get(config.get("model_env", ""), "") or config["model"]
        self.endpoint = self._resolve_endpoint(config)
        self.api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
        self.timeout = config.get("timeout_seconds", 20)
        self.token_param = config.get("token_param", "max_tokens")
        self.send_temperature = config.get("send_temperature", True)
        self.generation = generation

    @staticmethod
    def _resolve_endpoint(config: Dict[str, Any]) -> str:
        base = os.environ.get(config.get("endpoint_env", ""), "").strip()
        if base:
            # Env holds the base (".../openai/v1"); we own the route.
            return f"{base.rstrip('/')}/chat/completions"
        return config["endpoint"]

    def generate_json(self, system: str, user: str) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            self.token_param: self.generation.get("max_output_tokens", 800),
            "response_format": {"type": "json_object"},
        }
        if self.send_temperature:
            payload["temperature"] = self.generation.get("temperature", 0.3)
        try:
            resp = requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {_api_key(self.api_key_env, self.name)}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise LLMError(f"{self.name}: request timed out", retryable=True) from exc
        except requests.RequestException as exc:
            raise LLMError(f"{self.name}: {exc}", retryable=True) from exc

        if resp.status_code != 200:
            raise _classify(resp.status_code, resp.text, self.name)

        try:
            text = resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMError(
                f"{self.name}: unexpected response shape ({exc})", retryable=True
            ) from exc

        return self.parse_json_payload(text)


# azure_openai speaks the OpenAI protocol, so it reuses that adapter.
PROVIDER_TYPES = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "azure_openai": OpenAIProvider,
}


def build_provider(
    config: Dict[str, Any], generation: Dict[str, Any]
) -> Optional[LLMProvider]:
    """Instantiate one provider from its config block, or None if unknown."""
    cls = PROVIDER_TYPES.get(config.get("name", ""))
    return None if cls is None else cls(config, generation)


def has_credentials(config: Dict[str, Any]) -> bool:
    """True if this provider's key is present. Used to skip it without a call."""
    return bool(os.environ.get(config.get("api_key_env", ""), "").strip())
