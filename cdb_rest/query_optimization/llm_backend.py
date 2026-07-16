"""LLM backend abstraction for Layer 3 of the AI analysis engine.

Ollama (air-gapped/on-prem), OpenAI (cloud), and MockLLMBackend (tests) all
conform to BaseLLMBackend so the analysis layer never depends on a specific
provider. Selection happens via the CDB_LLM_BACKEND env var, mirroring how
CDB_AUTH_CLASS selects the auth backend (see cdb_rest/utils.py).
"""

import json
import logging
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class BaseLLMBackend(ABC):
    """A backend that turns (system_prompt, user_prompt) into a parsed JSON dict.

    Returns None -- never raises -- when the backend is unavailable, times out,
    or produces output that can't be parsed as JSON. Callers treat None exactly
    like "the LLM had nothing useful to add."
    """

    @abstractmethod
    def complete_json(self, system_prompt: str, user_prompt: str) -> Optional[dict]:
        raise NotImplementedError


class MockLLMBackend(BaseLLMBackend):
    """Returns a fixed, pre-recorded response. Used in unit tests and CI."""

    def __init__(self, response: Optional[dict] = None):
        self._response = response

    def complete_json(self, system_prompt, user_prompt):
        return self._response


class OllamaLLMBackend(BaseLLMBackend):
    """Local/air-gapped inference via Ollama's /api/generate endpoint."""

    def __init__(self, host=None, model=None, timeout=10):
        self.host = host or settings.CDB_OLLAMA_HOST
        self.model = model or settings.CDB_OLLAMA_MODEL
        self.timeout = timeout

    def complete_json(self, system_prompt, user_prompt):
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "format": "json",
            "stream": False,
        }
        body = self._post(f"{self.host}/api/generate", payload)
        if body is None:
            return None

        raw = body.get("response")
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            logger.warning("Ollama backend returned non-JSON response")
            return None

    def _post(self, url, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            logger.warning("Ollama backend request failed: %s", exc)
            return None


class OpenAILLMBackend(BaseLLMBackend):
    """Cloud inference via OpenAI's chat completions API, JSON mode enforced."""

    def __init__(self, api_key=None, model=None, timeout=15):
        self.api_key = api_key or settings.CDB_OPENAI_API_KEY
        self.model = model or settings.CDB_OPENAI_MODEL
        self.timeout = timeout

    def complete_json(self, system_prompt, user_prompt):
        if not self.api_key:
            logger.warning("OpenAI backend has no API key configured; skipping")
            return None

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        body = self._post(payload)
        if body is None:
            return None

        try:
            raw = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            logger.warning("OpenAI backend returned an unexpected response shape")
            return None

        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            logger.warning("OpenAI backend returned non-JSON message content")
            return None

    def _post(self, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            logger.warning("OpenAI backend request failed: %s", exc)
            return None


def get_llm_backend() -> Optional[BaseLLMBackend]:
    """Factory selecting a backend from CDB_LLM_BACKEND. Returns None (disabled)
    if unset or unrecognized, so LLM escalation is opt-in by default."""
    backend_name = (settings.CDB_LLM_BACKEND or "").strip().lower()
    if backend_name == "ollama":
        return OllamaLLMBackend()
    if backend_name == "openai":
        return OpenAILLMBackend()
    if backend_name == "mock":
        return MockLLMBackend()
    return None
