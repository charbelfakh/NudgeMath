"""Shared test doubles for LLM client mocking."""

from __future__ import annotations

from dataclasses import dataclass, field

from hint_engine.config import ModelConfig


@dataclass
class MockLLMClient:
    response: str
    calls: list[tuple[str, str]] = field(default_factory=list)

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self.response


@dataclass
class MockVisionClient:
    """Vision test double. Set ``raises`` to simulate an LLM/transport failure."""

    response: str = ""
    raises: Exception | None = None
    calls: list[tuple[str, str, str]] = field(default_factory=list)

    def complete_with_image(self, system: str, user: str, image_data_url: str) -> str:
        self.calls.append((system, user, image_data_url))
        if self.raises is not None:
            raise self.raises
        return self.response


TEST_GEN_CONFIG = ModelConfig(
    name="test-gen",
    provider="mock",
    base_url="http://mock.local/v1",
    model="test-model",
)

TEST_JUDGE_CONFIG = ModelConfig(
    name="test-judge",
    provider="mock",
    base_url="http://mock.local/v1",
    model="test-judge-model",
)

TEST_VISION_CONFIG = ModelConfig(
    name="test-vision",
    provider="mock",
    base_url="http://mock.local/v1",
    model="test-vision-model",
)
