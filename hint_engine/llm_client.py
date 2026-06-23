"""Provider-agnostic LLM completion interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from openai import APIError, OpenAI


@runtime_checkable
class LLMClient(Protocol):
    """Structural interface for text completion — easy to mock without inheritance."""

    def complete(self, system: str, user: str) -> str:
        """Return raw model text from a system + user prompt pair."""


class OpenAICompatibleClient:
    """OpenAI chat-completions client pointed at any compatible base URL."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        max_tokens: int = 512,
    ) -> None:
        self._model = model
        self._max_tokens = max_tokens
        self._client = OpenAI(
            base_url=base_url,
            api_key=api_key or "not-needed",
        )

    def complete(self, system: str, user: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=self._max_tokens,
            )
        except APIError as exc:
            raise RuntimeError(str(exc)) from exc
        message = response.choices[0].message
        return message.content or ""
