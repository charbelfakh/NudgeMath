import json

from hint_engine.models import TranscriptionResult
from hint_engine.transcribe import transcribe_problem
from hint_engine.vision_client import VisionClient
from tests.llm_mocks import TEST_VISION_CONFIG, MockVisionClient

_DATA_URL = "data:image/png;base64,ZmFrZS1pbWFnZQ=="


def test_transcribe_parses_canned_json():
    client = MockVisionClient(
        json.dumps({"problem": "Solve for x: 2x - 5 = 9", "student_answer": "x = 2"})
    )
    result = transcribe_problem(_DATA_URL, client=client, config=TEST_VISION_CONFIG)

    assert isinstance(result, TranscriptionResult)
    assert result.problem == "Solve for x: 2x - 5 = 9"
    assert result.student_answer == "x = 2"
    assert result.meta["model"] == TEST_VISION_CONFIG.model
    assert result.meta["provider"] == "mock"
    assert "latency_ms" in result.meta
    assert "error" not in result.meta


def test_transcribe_passes_image_to_client():
    client = MockVisionClient(json.dumps({"problem": "3 + 4", "student_answer": ""}))
    transcribe_problem(_DATA_URL, client=client, config=TEST_VISION_CONFIG)

    assert len(client.calls) == 1
    _system, _user, image = client.calls[0]
    assert image == _DATA_URL


def test_transcribe_defaults_missing_student_answer_to_empty():
    client = MockVisionClient(json.dumps({"problem": "What is 7 x 8?"}))
    result = transcribe_problem(_DATA_URL, client=client, config=TEST_VISION_CONFIG)

    assert result.problem == "What is 7 x 8?"
    assert result.student_answer == ""


def test_transcribe_strips_code_fences():
    client = MockVisionClient(
        "```json\n" + json.dumps({"problem": "2 + 2", "student_answer": "5"}) + "\n```"
    )
    result = transcribe_problem(_DATA_URL, client=client, config=TEST_VISION_CONFIG)

    assert result.problem == "2 + 2"
    assert "error" not in result.meta


def test_transcribe_empty_response_surfaces_error():
    result = transcribe_problem(
        _DATA_URL, client=MockVisionClient(""), config=TEST_VISION_CONFIG
    )
    assert result.problem == ""
    assert "empty response" in result.meta["error"].lower()


def test_transcribe_tolerates_trailing_comma():
    client = MockVisionClient('{"problem": "2 + 2", "student_answer": "5",}')
    result = transcribe_problem(_DATA_URL, client=client, config=TEST_VISION_CONFIG)
    assert result.problem == "2 + 2"
    assert result.student_answer == "5"
    assert "error" not in result.meta


def test_transcribe_extracts_json_embedded_in_prose():
    client = MockVisionClient(
        'Here is the transcription:\n{"problem": "3x = 12", "student_answer": ""}\nDone.'
    )
    result = transcribe_problem(_DATA_URL, client=client, config=TEST_VISION_CONFIG)
    assert result.problem == "3x = 12"
    assert "error" not in result.meta


def test_transcribe_regex_fallback_on_broken_json():
    # Malformed JSON (no closing brace) — the problem field is still recovered.
    client = MockVisionClient('{"problem": "Solve for x: 2x - 5 = 9" oops truncated')
    result = transcribe_problem(_DATA_URL, client=client, config=TEST_VISION_CONFIG)
    assert result.problem == "Solve for x: 2x - 5 = 9"
    assert "error" not in result.meta


def test_transcribe_uses_plaintext_reply_as_problem():
    client = MockVisionClient("What is 7 x 8?")
    result = transcribe_problem(_DATA_URL, client=client, config=TEST_VISION_CONFIG)
    assert result.problem == "What is 7 x 8?"
    assert "error" not in result.meta


def test_transcribe_client_failure_surfaces_error():
    client = MockVisionClient(raises=RuntimeError("vision model unreachable"))
    result = transcribe_problem(_DATA_URL, client=client, config=TEST_VISION_CONFIG)

    assert result.problem == ""
    assert result.meta["error"] == "vision model unreachable"


def test_mock_vision_client_satisfies_protocol():
    assert isinstance(MockVisionClient(), VisionClient)


def test_transcription_result_is_answer_blind():
    # The transcription shape must never carry a correct answer into the pipeline.
    assert not hasattr(TranscriptionResult(problem="x"), "correct_answer")
