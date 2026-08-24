from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any
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

    def generate(self, system_prompt: str, context: dict[str, Any], request: str) -> str:
        raise ProviderUnavailableError("AI assistance is unavailable because no provider is configured.")


class OpenAICompatibleProvider(AIProvider):
    name = "openai-compatible"

    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def generate(self, system_prompt: str, context: dict[str, Any], request: str) -> str:
        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps({"request": request, "context": context})},
            ],
            "temperature": 0,
        }).encode("utf-8")
        response = urlopen(Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        ), timeout=30)
        payload = json.loads(response.read().decode("utf-8"))
        return str(payload["choices"][0]["message"]["content"])