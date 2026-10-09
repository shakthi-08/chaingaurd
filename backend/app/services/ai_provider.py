from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AIProvider(ABC):
    name = "unknown"

    @abstractmethod
    def generate(self, system_prompt: str, context: dict[str, Any], request: str) -> str:
        raise NotImplementedError


class ProviderUnavailableError(RuntimeError):
    pass


class UnavailableAIProvider(AIProvider):
    name = "unavailable"

    def __init__(self, reason: str | None = None) -> None:
        self.reason = reason or (
            "AI assistance is unavailable because no provider is configured (AI_PROVIDER=none). "
            "Set AI_PROVIDER=openai with AI_API_KEY, or AI_PROVIDER=ollama."
        )

    def generate(self, system_prompt: str, context: dict[str, Any], request: str) -> str:
        raise ProviderUnavailableError(self.reason)


class OpenAICompatibleProvider(AIProvider):
    name = "openai-compatible"

    def __init__(self, api_key: str, model: str, base_url: str, timeout: int = 60) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = max(1, int(timeout))

    def generate(self, system_prompt: str, context: dict[str, Any], request: str) -> str:
        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps({"request": request, "context": context}, default=str)},
            ],
            "temperature": 0,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            response = urlopen(Request(
                f"{self.base_url}/chat/completions",
                data=body,
                headers=headers,
                method="POST",
            ), timeout=self.timeout)
            payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise ProviderUnavailableError(
                f"AI provider HTTP {exc.code}: {detail or exc.reason}"
            ) from exc
        except URLError as exc:
            raise ProviderUnavailableError(f"Unable to reach AI provider at {self.base_url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ProviderUnavailableError(f"AI provider timed out after {self.timeout}s.") from exc

        try:
            return str(payload["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderUnavailableError("AI provider returned an unexpected response payload.") from exc
