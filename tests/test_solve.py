"""Tests for the admin-only solver path (LLM mocked)."""

from __future__ import annotations

import json

from hint_engine.solve import solve_problem
from tests.llm_mocks import TEST_GEN_CONFIG, MockLLMClient


def test_solve_problem_parses_solution_json():
    client = MockLLMClient(
        json.dumps(
            {
                "solution_text": "1. Add 5 to both sides: 2x = 14\n2. Divide by 2: x = 7",
                "final_answer": "x = 7",
            }
        )
    )
    solution = solve_problem(
        "Solve for x: 2x - 5 = 9", "7", client=client, config=TEST_GEN_CONFIG
    )
    assert solution.final_answer == "x = 7"
    assert "Divide by 2" in solution.solution_text
    assert solution.meta["provider"] == "mock"
    assert solution.meta["model"] == "test-model"
    assert solution.meta.get("error") is None
    assert len(client.calls) == 1


def test_solve_problem_prompt_includes_problem_and_grade():
    client = MockLLMClient(json.dumps({"solution_text": "s", "final_answer": "a"}))
    solve_problem("What is 2 + 2?", "3", client=client, config=TEST_GEN_CONFIG)
    system, user = client.calls[0]
    assert "strict JSON" in system
    assert "What is 2 + 2?" in user
    assert "Grade level: 3" in user


def test_solve_problem_surfaces_parse_error_and_keeps_raw_text():
    client = MockLLMClient("Just plain prose, no JSON.")
    solution = solve_problem("2x = 4", client=client, config=TEST_GEN_CONFIG)
    assert solution.solution_text == "Just plain prose, no JSON."
    assert solution.final_answer == ""
    assert "JSON parse error" in solution.meta["error"]
    assert solution.meta["raw_response"]


def test_solve_problem_surfaces_client_error():
    class FailingClient:
        def complete(self, system: str, user: str) -> str:
            raise RuntimeError("model unreachable")

    solution = solve_problem("2x = 4", client=FailingClient(), config=TEST_GEN_CONFIG)
    assert solution.solution_text == ""
    assert solution.meta["error"] == "model unreachable"


def test_solve_problem_builds_client_with_thinking_and_headroom(monkeypatch):
    """Solving keeps model reasoning on (with budget to spare) — unlike hints,
    where thinking is disabled so the visible reply is not starved."""
    import hint_engine.solve as solve_mod

    captured: dict = {}

    def fake_factory(config, *, max_tokens, thinking=False):
        captured.update(max_tokens=max_tokens, thinking=thinking)
        return MockLLMClient(
            json.dumps({"solution_text": "s", "final_answer": "a"})
        )

    monkeypatch.setattr(solve_mod, "client_from_config", fake_factory)
    solve_problem("2x = 4", config=TEST_GEN_CONFIG)
    assert captured["thinking"] is True
    assert captured["max_tokens"] >= 4096
