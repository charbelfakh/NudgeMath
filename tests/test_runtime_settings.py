"""Tests for the shared admin-override state (lock-guarded, process-wide)."""

from __future__ import annotations

import threading

from hint_engine.config import ANTHROPIC_SONNET, CLAUDE_SUBSCRIPTION, OLLAMA_DEFAULT
from hint_engine.runtime_settings import RuntimeSettings


def test_model_override_roundtrip_and_clear():
    settings = RuntimeSettings()
    assert settings.get_model_override("generation") is None

    settings.set_model_override("generation", OLLAMA_DEFAULT)
    assert settings.get_model_override("generation") is OLLAMA_DEFAULT
    assert settings.get_model_override("vision") is None  # kinds are independent

    settings.clear_model_override("generation")
    assert settings.get_model_override("generation") is None
    settings.clear_model_override("generation")  # idempotent


def test_clear_overrides_for_provider_covers_every_kind():
    """A new model kind must be cleaned up on disconnect without editing a list."""
    settings = RuntimeSettings()
    for kind in ("generation", "vision", "solver", "some_future_kind"):
        settings.set_model_override(kind, CLAUDE_SUBSCRIPTION)
    settings.set_model_override("judge", ANTHROPIC_SONNET)  # different provider

    settings.clear_overrides_for_provider("claude_subscription")

    for kind in ("generation", "vision", "solver", "some_future_kind"):
        assert settings.get_model_override(kind) is None, kind
    assert settings.get_model_override("judge") is ANTHROPIC_SONNET  # untouched


def test_effort_roundtrip_and_reset():
    settings = RuntimeSettings()
    assert settings.get_claude_effort() is None
    settings.set_claude_effort("max")
    assert settings.get_claude_effort() == "max"

    settings.reset()
    assert settings.get_claude_effort() is None
    assert settings.get_model_override("generation") is None


def test_concurrent_writes_do_not_corrupt_state():
    """Resolvers run on a thread pool; the override map is shared mutable state."""
    settings = RuntimeSettings()
    kinds = [f"kind_{i}" for i in range(50)]
    errors: list[BaseException] = []

    def hammer(kind: str) -> None:
        try:
            for _ in range(200):
                settings.set_model_override(kind, OLLAMA_DEFAULT)
                settings.get_model_override(kind)
                settings.clear_overrides_for_provider("anthropic")  # concurrent scan
                settings.clear_model_override(kind)
        except BaseException as exc:  # noqa: BLE001 - surface any race
            errors.append(exc)

    threads = [threading.Thread(target=hammer, args=(k,)) for k in kinds]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors, errors
    # Every kind was cleared by its own thread; nothing leaked.
    assert all(settings.get_model_override(k) is None for k in kinds)
