import pytest

from hint_engine.curriculum import (
    CURRICULUM,
    band_for_grade,
    default_template_topic,
    find_topic,
    topics_for_band,
)


def test_curriculum_loads_all_bands():
    bands = {t.grade_band for t in CURRICULUM}
    assert bands == {"elementary", "middle", "high"}


def test_every_band_has_a_template_topic():
    for band in ("elementary", "middle", "high"):
        entry = default_template_topic(band)
        assert entry.template is True
        assert entry.grade_band == band


@pytest.mark.parametrize(
    "grade,expected",
    [
        ("K", "elementary"),
        ("3", "elementary"),
        ("6", "middle"),
        ("8", "middle"),
        ("9", "high"),
        ("12", "high"),
        ("middle", "middle"),
    ],
)
def test_band_for_grade(grade, expected):
    assert band_for_grade(grade) == expected


def test_band_for_grade_rejects_unknown():
    with pytest.raises(ValueError):
        band_for_grade("college")


def test_find_topic_and_topics_for_band():
    assert find_topic("middle", "linear_equations") is not None
    assert find_topic("middle", "quadratics") is None
    assert {t.topic for t in topics_for_band("high")} == {
        "quadratics",
        "functions",
        "geometry",
    }


def test_geometry_is_a_template_topic_in_every_band():
    for band in ("elementary", "middle", "high"):
        entry = find_topic(band, "geometry")
        assert entry is not None and entry.template is True


def test_default_template_topic_unaffected_by_geometry():
    # Geometry is appended after each band's original template topic, so the
    # default (topic-less) generation target does not change.
    assert default_template_topic("elementary").topic == "arithmetic"
    assert default_template_topic("middle").topic == "linear_equations"
    assert default_template_topic("high").topic == "quadratics"
