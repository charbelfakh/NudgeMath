"""K-12 curriculum taxonomy.

The taxonomy lives in ``data/curriculum.jsonl`` (one topic per line) so it can grow as
data without touching Python. Each entry names a grade band, a topic, whether a
deterministic template generator exists for it (``template``), and its difficulty
levels. Consumed by ``problem_gen`` to pick and generate grade-appropriate problems.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "curriculum.jsonl"

# Numeric grade -> band. "K" maps to elementary.
_BAND_BY_GRADE = {
    "K": "elementary",
    **{str(g): "elementary" for g in range(0, 6)},
    **{str(g): "middle" for g in range(6, 9)},
    **{str(g): "high" for g in range(9, 13)},
}


@dataclass(frozen=True)
class CurriculumTopic:
    grade_band: str
    grade_range: str
    topic: str
    template: bool
    difficulties: tuple[str, ...]
    description: str


def load_curriculum(path: Path = DATA_PATH) -> list[CurriculumTopic]:
    """Parse the JSONL taxonomy into CurriculumTopic objects, preserving file order."""
    topics: list[CurriculumTopic] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name}:{line_no}: invalid JSON — {exc}") from exc
        topics.append(
            CurriculumTopic(
                grade_band=obj["grade_band"],
                grade_range=obj["grade_range"],
                topic=obj["topic"],
                template=bool(obj.get("template", False)),
                difficulties=tuple(obj.get("difficulties", ["medium"])),
                description=obj.get("description", ""),
            )
        )
    return topics


CURRICULUM: list[CurriculumTopic] = load_curriculum()


def band_for_grade(grade_level: str) -> str:
    """Map a grade ('K', '3', '7', '11') or a band name to a grade band.

    Raises ValueError for anything unrecognized.
    """
    key = grade_level.strip()
    if key in _BAND_BY_GRADE:
        return _BAND_BY_GRADE[key]
    lowered = key.lower()
    if lowered in {"elementary", "middle", "high"}:
        return lowered
    raise ValueError(f"Unrecognized grade level: {grade_level!r}")


def topics_for_band(grade_band: str) -> list[CurriculumTopic]:
    return [t for t in CURRICULUM if t.grade_band == grade_band]


def find_topic(grade_band: str, topic: str) -> CurriculumTopic | None:
    for entry in CURRICULUM:
        if entry.grade_band == grade_band and entry.topic == topic:
            return entry
    return None


def default_template_topic(grade_band: str) -> CurriculumTopic:
    """The first template-backed topic for a band — used when no topic is requested."""
    for entry in topics_for_band(grade_band):
        if entry.template:
            return entry
    raise ValueError(f"No template-backed topic for grade band {grade_band!r}")
