"""Shared test fixtures."""

from __future__ import annotations

import pytest

from hint_engine import rate_limit
from hint_engine.runtime_settings import SETTINGS


@pytest.fixture(autouse=True)
def reset_process_state():
    """Rate-limit buckets and admin overrides are process-wide: without this, one
    test's writes leak into the next and it fails for the wrong reason."""
    rate_limit.reset_all()
    SETTINGS.reset()
    yield
    rate_limit.reset_all()
    SETTINGS.reset()
