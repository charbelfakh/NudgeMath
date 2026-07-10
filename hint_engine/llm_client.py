"""Provider-agnostic LLM completion interface."""

from __future__ import annotations

import threading
from typing import Protocol, runtime_checkable

import httpx
from openai import APIError, OpenAI


@runtime_checkable
class LLMClient(Protocol):
    """Structural interface for text completion — easy to mock without inheritance."""

    def complete(self, system: str, user: str) -> str:
        """Return raw model text from a system + user prompt pair."""


def truncation_error(max_tokens: int) -> RuntimeError:
    """The error every client raises when the model hit its output ceiling.

    A truncated reply is worthless to callers that parse strict JSON — it either
    fails to parse (a confusing "Unterminated string" error) or, worse, parses
    into a silently incomplete hint. Raising here turns it into one actionable
    message on ``meta["error"]`` instead.
    """
    return RuntimeError(
        f"Model response was truncated at max_tokens={max_tokens}. "
        "Raise the token budget, shorten the prompt, or lower the Claude effort level."
    )


class OpenAICompatibleClient:
    """OpenAI chat-completions client pointed at any compatible base URL."""

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
        # "none" disables thinking on reasoning models (e.g. qwen3 via Ollama) so they
        # return an answer instead of empty content. Left unset for providers that
        # reject the parameter.
        self._reasoning_effort = reasoning_effort
        self._client = OpenAI(
            base_url=base_url,
            api_key=api_key or "not-needed",
        )

    def complete(self, system: str, user: str) -> str:
        extra = {}
        if self._reasoning_effort is not None:
            extra["reasoning_effort"] = self._reasoning_effort
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
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


# Anthropic gates subscription (Bearer) tokens to Claude Code: the Messages API
# only accepts them when the system prompt's FIRST block is exactly this identity
# string — without it the API returns a disguised 429. This makes requests
# identify as Claude Code, which is outside Anthropic's intended use of
# subscription tokens. Acceptable for personal use of your own account; do NOT
# redistribute an app relying on this — use an API-key ("anthropic") config
# instead.
CLAUDE_CODE_IDENTITY = "You are Claude Code, Anthropic's official CLI for Claude."
ANTHROPIC_VERSION = "2023-06-01"

# One pooled connection shared by every subscription client. Instances are
# constructed per request (client_from_config), so an instance-owned client
# would leak an unclosed pool each call and never reuse connections.
_SHARED_HTTP_TIMEOUT_S = 300.0
_shared_http_client: httpx.Client | None = None
# Resolvers run on a thread pool: without the lock two concurrent first-requests
# each build a client and the loser's pool leaks.
_http_client_lock = threading.Lock()


def _http_client() -> httpx.Client:
    global _shared_http_client
    if _shared_http_client is None:
        with _http_client_lock:
            if _shared_http_client is None:  # re-check under the lock
                _shared_http_client = httpx.Client(timeout=_SHARED_HTTP_TIMEOUT_S)
    return _shared_http_client


def close_http_client() -> None:
    """Close the pooled client (FastAPI shutdown hook, tests)."""
    global _shared_http_client
    with _http_client_lock:
        if _shared_http_client is not None:
            _shared_http_client.close()
            _shared_http_client = None


class ClaudeSubscriptionClient:
    """Anthropic Messages API client authenticated by the subscription OAuth token.

    Satisfies the :class:`LLMClient` protocol (``complete(system, user)``). The
    token comes from :mod:`hint_engine.claude_oauth`; it auto-refreshes before
    expiry. This path is answer-blind exactly like every other ``LLMClient`` —
    it only relays the system + user prompts ``generate_hint`` builds.
    """

    def __init__(
        self,
        *,
        model: str,
        base_url: str = "https://api.anthropic.com",
        max_tokens: int = 512,
        thinking: bool = False,
        effort: str | None = None,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._max_tokens = max_tokens
        # Claude 5 models think adaptively by default and can burn the whole
        # max_tokens budget on thinking blocks, returning empty/truncated text
        # (the Anthropic twin of the Ollama reasoning_effort="none" issue). Off
        # by default; the solver opts in (with a bigger budget) where reasoning
        # actually helps.
        self._thinking = thinking
        # output_config.effort ("low"…"max"); None = the API default ("high").
        # Callers must not pass it for models that reject it (Haiku).
        self._effort = effort
        self._client = _http_client()

    def _headers(self) -> dict[str, str]:
        # Imported here (not at module top) to keep llm_client free of a config
        # import cycle; claude_oauth only depends on httpx.
        from hint_engine import claude_oauth

        token = claude_oauth.valid_access_token()
        if not token:
            raise RuntimeError(
                "Not signed in — connect Claude (subscription) in Settings first."
            )
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "anthropic-version": ANTHROPIC_VERSION,
            "anthropic-beta": claude_oauth.OAUTH_BETA_HEADER,
        }

    def _post_messages(self, content: str | list[dict], system: str) -> str:
        """Send one user message (text or content blocks) and return the text reply.

        Shared by the text path and the vision subclass
        (``vision_client.ClaudeSubscriptionVisionClient``)."""
        system_blocks = [{"type": "text", "text": CLAUDE_CODE_IDENTITY}]
        if system:
            system_blocks.append({"type": "text", "text": system})
        payload = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": system_blocks,
            "messages": [{"role": "user", "content": content}],
        }
        # Always explicit: omitting `thinking` means adaptive on Sonnet 5 but
        # OFF on Opus — the solver's opt-in must survive a model switch.
        payload["thinking"] = (
            {"type": "adaptive"} if self._thinking else {"type": "disabled"}
        )
        if self._effort is not None:
            payload["output_config"] = {"effort": self._effort}
        # Callers (generate/judge/solve/transcribe) catch RuntimeError and surface
        # it into meta["error"]; transport failures must not escape as httpx types.
        try:
            response = self._client.post(
                f"{self._base_url}/v1/messages",
                headers=self._headers(),
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Anthropic API request failed: {exc}") from exc
        if response.status_code >= 400:
            body = response.text[:300]
            raise RuntimeError(f"Anthropic API error {response.status_code}: {body}")
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(f"Anthropic API returned invalid JSON: {exc}") from exc
        # A high effort level can spend the whole budget on thinking blocks and
        # return truncated (or empty) text — surface that instead of parsing it.
        if data.get("stop_reason") == "max_tokens":
            raise truncation_error(self._max_tokens)
        return "".join(
            block.get("text", "")
            for block in data.get("content") or []
            if block.get("type") == "text"
        )

    def complete(self, system: str, user: str) -> str:
        return self._post_messages(user, system)

