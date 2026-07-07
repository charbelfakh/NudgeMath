import json

from hint_engine.eval_cases import DATA_PATH, EVAL_CASES, load_eval_cases
from hint_engine.evaluation import run_deterministic_checks
from hint_engine.models import Hint
from hint_engine.run_eval import write_json_report


def test_dataset_loads_from_jsonl():
    cases = load_eval_cases()
    assert cases[0].case_id == "algebra_sign_error"
    assert cases[0].correct_answer == "x = 7"
    # Externalized dataset is the same object the package exports.
    assert len(cases) == len(EVAL_CASES)
    assert len(cases) >= 20  # grown well beyond the original 10 seeds


def test_dataset_case_ids_unique_and_present():
    ids = [case.case_id for case in EVAL_CASES]
    assert all(ids)
    assert len(ids) == len(set(ids))


def test_dataset_file_line_count_matches_loaded_cases():
    lines = [ln for ln in DATA_PATH.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == len(EVAL_CASES)


def test_write_json_report_round_trips(tmp_path):
    case = EVAL_CASES[0]
    hint = Hint(hint_text="Re-check the sign step.", reveals_answer=False, meta={"model": "m"})
    reports = [run_deterministic_checks(case, hint)]

    out = tmp_path / "nested" / "report.json"
    write_json_report(reports, out)

    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(loaded, list)
    assert loaded[0]["case_id"] == "algebra_sign_error"
    assert loaded[0] == reports[0].to_dict()
