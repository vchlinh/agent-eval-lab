"""
Provider interface: abstracts "send these messages, get text back" so
react_agent.py never depends on which model or API is behind it. One
provider (local Ollama) is implemented now; a second is cheap to add
later because nothing else in the agent needs to change.
"""

from __future__ import annotations

import dataclasses
import json
import time
import urllib.request


@dataclasses.dataclass
class ProviderResult:
    text: str
    tokens_in: int
    tokens_out: int
    latency_ms: float


class Provider:
    def complete(self, messages: list[dict]) -> ProviderResult:
        raise NotImplementedError


class OllamaProvider(Provider):
    """Talks to a local Ollama server's /api/chat endpoint."""

    def __init__(
        self,
        model: str,
        host: str = "http://localhost:11434",
        temperature: float = 0.2,
        timeout_seconds: int = 120,
    ):
        self.model = model
        self.host = host
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds

    def complete(self, messages: list[dict]) -> ProviderResult:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        request = urllib.request.Request(
            f"{self.host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        start = time.monotonic()
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            data = json.loads(response.read())
        latency_ms = (time.monotonic() - start) * 1000

        return ProviderResult(
            text=data["message"]["content"],
            tokens_in=data.get("prompt_eval_count", 0),
            tokens_out=data.get("eval_count", 0),
            latency_ms=latency_ms,
        )
