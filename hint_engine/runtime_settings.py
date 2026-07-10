"""Process-wide admin settings that override env + defaults at runtime.

The admin panel can repoint a model kind at a preset and set the Claude effort
level. Both are the same shape of state — mutable, process-wide, cleared on
restart — so they live in one lock-guarded object instead of a dict and a bare
`global` that every new knob would copy a third time.

**Thread-safety:** resolvers run on a thread pool, so writers take a lock and
readers see a consistent snapshot of one field. **Scope:** per-process. With
several uvicorn workers an admin's switch lands on one worker only; run a single
worker, or move this behind Redis the way ``ProblemStore`` already is.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hint_engine.config import ModelConfig


class RuntimeSettings:
    """Admin overrides layered over env + defaults (``override › env › default``)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model_overrides: dict[str, ModelConfig] = {}
        self._claude_effort: str | None = None

    # --- model overrides ------------------------------------------------------

    def get_model_override(self, kind: str) -> ModelConfig | None:
        with self._lock:
            return self._model_overrides.get(kind)

    def set_model_override(self, kind: str, config: ModelConfig) -> None:
        with self._lock:
            self._model_overrides[kind] = config

    def clear_model_override(self, kind: str) -> None:
        with self._lock:
            self._model_overrides.pop(kind, None)

    def clear_overrides_for_provider(self, provider: str) -> None:
        """Drop every kind whose override points at ``provider``.

        Used when a provider's credential goes away (subscription disconnect), so
        no model kind keeps routing to a client that can no longer authenticate.
        Iterates every kind — a new kind is covered automatically.
        """
        with self._lock:
            stale = [
                kind
                for kind, cfg in self._model_overrides.items()
                if cfg.provider == provider
            ]
            for kind in stale:
                del self._model_overrides[kind]

    # --- Claude effort --------------------------------------------------------

    def get_claude_effort(self) -> str | None:
        with self._lock:
            return self._claude_effort

    def set_claude_effort(self, effort: str | None) -> None:
        with self._lock:
            self._claude_effort = effort

    # --- lifecycle ------------------------------------------------------------

    def reset(self) -> None:
        """Drop every override (tests; admin recovery)."""
        with self._lock:
            self._model_overrides.clear()
            self._claude_effort = None


SETTINGS = RuntimeSettings()
