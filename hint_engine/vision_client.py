"""Provider-agnostic multimodal (image + text) completion interface.

Kept separate from ``llm_client.LLMClient`` so the text-only hint/judge pipeline
stays pure; only transcription reaches for a vision model.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from openai import APIError, OpenAI

from hint_engine.llm_client import ClaudeSubscriptionClient, truncation_error


@runtime_checkable
class VisionClient(Protocol):
    """Structural interface for image+text completion — mockable without inheritance."""

    def complete_with_image(self, system: str, user: str, image_data_url: str) -> str:
        """Return raw model text from a system + user prompt plus one image (data URL)."""


class OpenAICompatibleVisionClient:
    """OpenAI chat-completions client that attaches one image content part."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        max_tokens: int = 512,
        reasoning_effort: str | None = None,
    ) -> None:
        self._model = model
        self._max_tokens = max_tokens
        # For reasoning models (e.g. qwen3 via Ollama), "none" disables thinking so
        # the model emits the answer instead of exhausting the budget on reasoning
        # and returning empty content. Left unset for providers that reject it.
        self._reasoning_effort = reasoning_effort
        self._client = OpenAI(
            base_url=base_url,
            api_key=api_key or "not-needed",
        )

    def complete_with_image(self, system: str, user: str, image_data_url: str) -> str:
        extra = {}
        if self._reasoning_effort is not None:
            extra["reasoning_effort"] = self._reasoning_effort
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user},
                            {"type": "image_url", "image_url": {"url": image_data_url}},
                        ],
                    },
                ],
                max_tokens=self._max_tokens,
                **extra,
            )
        except APIError as exc:
            raise RuntimeError(str(exc)) from exc
        choice = response.choices[0]
        if getattr(choice, "finish_reason", None) == "length":
            raise truncation_error(self._max_tokens)
        return choice.message.content or ""


def _split_image_data_url(image_data_url: str) -> tuple[str, str]:
    """Split ``data:<media>;base64,<payload>`` into (media_type, base64 payload)."""
    header, sep, data = image_data_url.partition(",")
    if not sep or not header.startswith("data:") or "base64" not in header:
        raise RuntimeError("Expected a base64 image data: URL")
    media_type = header[len("data:") :].split(";", 1)[0] or "image/png"
    return media_type, data


class ClaudeSubscriptionVisionClient(ClaudeSubscriptionClient):
    """Vision variant of the subscription client (Claude models are multimodal).

    Reuses the text client's auth/transport and sends the image as an Anthropic
    base64 ``source`` block. Like every ``VisionClient`` it only transcribes —
    the prompts come from ``transcribe_problem``, which never asks to solve.
    """

    def complete_with_image(self, system: str, user: str, image_data_url: str) -> str:
        media_type, data = _split_image_data_url(image_data_url)
        content = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": data},
            },
            {"type": "text", "text": user},
        ]
        return self._post_messages(content, system)
