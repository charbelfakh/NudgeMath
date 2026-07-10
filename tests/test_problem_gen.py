import json
import re

import pytest

from hint_engine.models import GeneratedProblem, HintRequest
from hint_engine.problem_gen import generate_problem
from tests.llm_mocks import TEST_GEN_CONFIG, MockLLMClient


def test_template_is_deterministic_with_seed():
    a = generate_problem("3", topic="arithmetic", seed=42)
    b = generate_problem("3", topic="arithmetic", seed=42)
    assert (a.problem, a.correct_answer) == (b.problem, b.correct_answer)
    assert a.source == "template"
    assert a.verified is True


def test_arithmetic_answer_is_exact():
    for seed in range(25):
        gp = generate_problem("4", topic="arithmetic", difficulty="hard", seed=seed)
        m = re.match(r"What is (\d+) ([+\-×]) (\d+)\?", gp.problem)
        assert m, gp.problem
        x, op, y = int(m.group(1)), m.group(2), int(m.group(3))
        expected = {"+": x + y, "-": x - y, "×": x * y}[op]
        assert gp.correct_answer == str(expected)


def test_linear_equation_solution_satisfies_equation():
    for seed in range(25):
        gp = generate_problem("7", topic="linear_equations", seed=seed)
        m = re.match(r"Solve for x: (\d+)x ([+-]) (\d+) = (-?\d+)", gp.problem)
        assert m, gp.problem
        a = int(m.group(1))
        b = int(m.group(3)) * (1 if m.group(2) == "+" else -1)
        c = int(m.group(4))
        x = int(re.match(r"x = (-?\d+)", gp.correct_answer).group(1))
        assert a * x + b == c


def _parse_quadratic(problem: str) -> tuple[int, int]:
    body = problem.split(":", 1)[1].split("=")[0].strip()  # e.g. "x^2 + 3x - 10"
    b_match = re.search(r"([+-])\s*(\d+)x", body)
    c_match = re.search(r"([+-])\s*(\d+)\s*$", body)
    b = int(b_match.group(1) + b_match.group(2)) if b_match else 0
    c = int(c_match.group(1) + c_match.group(2)) if c_match else 0
    return b, c


def test_quadratic_roots_satisfy_equation():
    for seed in range(25):
        gp = generate_problem("10", topic="quadratics", seed=seed)
        b, c = _parse_quadratic(gp.problem)
        roots = [int(r) for r in re.findall(r"x = (-?\d+)", gp.correct_answer)]
        assert roots, gp.correct_answer
        for r in roots:
            assert r * r + b * r + c == 0


def _verify_geometry(problem: str, answer: str) -> None:
    nums = [int(n) for n in re.findall(r"\d+", problem)]
    ans = int(answer)
    if "area" in problem and "rectangle" in problem:
        assert nums[0] * nums[1] == ans
    elif "perimeter" in problem:
        assert 2 * (nums[0] + nums[1]) == ans
    elif "hypotenuse" in problem or "leg" in problem:
        legs_and_hyp = sorted(nums + [ans])
        a, b, c = legs_and_hyp
        assert a * a + b * b == c * c
    elif "base" in problem:
        assert nums[0] * nums[1] % 2 == 0
        assert nums[0] * nums[1] // 2 == ans
    elif "third angle" in problem:
        assert nums[0] + nums[1] + ans == 180
    elif "straight line" in problem:
        assert nums[0] + ans == 180
    else:
        raise AssertionError(f"Unrecognized geometry problem: {problem!r}")


def test_geometry_is_deterministic_with_seed():
    a = generate_problem("7", topic="geometry", seed=11)
    b = generate_problem("7", topic="geometry", seed=11)
    assert (a.problem, a.correct_answer) == (b.problem, b.correct_answer)


def test_geometry_answers_are_exact_across_seeds_and_bands():
    for grade in ("4", "7", "11"):  # geometry exists in every band
        for difficulty in ("easy", "medium", "hard"):
            for seed in range(40):
                gp = generate_problem(
                    grade, topic="geometry", difficulty=difficulty, seed=seed
                )
                assert gp.source == "template"
                assert gp.verified is True
                _verify_geometry(gp.problem, gp.correct_answer)


def test_default_topic_used_when_none_requested():
    assert generate_problem("2", seed=1).topic == "arithmetic"
    assert generate_problem("7", seed=1).topic == "linear_equations"
    assert generate_problem("11", seed=1).topic == "quadratics"


def test_unknown_topic_raises():
    with pytest.raises(ValueError):
        generate_problem("5", topic="calculus")


def test_template_mode_on_non_template_topic_raises():
    # 'fractions' has no template generator; template mode must fail loudly.
    with pytest.raises(ValueError):
        generate_problem("4", topic="fractions", mode="template")


def test_llm_mode_uses_client_and_marks_unverified():
    client = MockLLMClient(
        json.dumps({"problem": "A pizza is cut into 8 slices...", "correct_answer": "3/8"})
    )
    gp = generate_problem(
        "4", topic="fractions", mode="llm", client=client, config=TEST_GEN_CONFIG
    )
    assert isinstance(gp, GeneratedProblem)
    assert gp.source == "llm"
    assert gp.verified is False
    assert gp.problem.startswith("A pizza")
    assert gp.correct_answer == "3/8"
    assert gp.meta["provider"] == "mock"


def test_auto_mode_falls_back_to_llm_for_non_template_topic():
    client = MockLLMClient(json.dumps({"problem": "Ratio problem", "correct_answer": "2:3"}))
    gp = generate_problem(
        "7", topic="ratios", mode="auto", client=client, config=TEST_GEN_CONFIG
    )
    assert gp.source == "llm"


def test_llm_mode_surfaces_parse_error():
    gp = generate_problem(
        "4",
        topic="fractions",
        mode="llm",
        client=MockLLMClient("not json"),
        config=TEST_GEN_CONFIG,
    )
    assert gp.problem == ""
    assert "error" in gp.meta


def test_generated_answer_never_enters_hint_request():
    # The answer-blind boundary: a HintRequest built from a generated problem
    # carries no correct answer, even though the generator knows it.
    gp = generate_problem("7", seed=3)
    assert gp.correct_answer  # generator knows the answer
    request = HintRequest(problem=gp.problem, student_answer="0")
    assert not hasattr(request, "correct_answer")
