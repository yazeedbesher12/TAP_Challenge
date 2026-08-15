import copy
import json
from pathlib import Path

import pytest

from app import assessment_result_html
from src.config import SKILL_ASSESSMENTS_PATH
from src.data_loader import load_skill_assessments, validate_skill_assessments
from src.skill_assessment import (
    assessment_questions,
    calculate_assessment_result,
    find_skill_assessment,
    select_assessment_skills,
)


def catalog():
    return load_skill_assessments(SKILL_ASSESSMENTS_PATH)


def test_valid_assessment_json_loading():
    data = catalog()
    assert isinstance(data["assessments"], list) and len(data["assessments"]) == 10
    assert data["assessment_rules"]["questions_per_skill"] == 3
    assert data["assessment_rules"]["passing_score_percentage"] == 67


def test_missing_and_invalid_assessment_file_behavior(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Skill-assessment file is missing"):
        load_skill_assessments(tmp_path / "missing.json")
    malformed = tmp_path / "malformed.json"
    malformed.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="Could not read skill assessments"):
        load_skill_assessments(malformed)
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps({"assessments": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="catalogue is missing"):
        load_skill_assessments(invalid)


def test_duplicate_question_id_is_rejected():
    data = copy.deepcopy(catalog())
    data["assessments"][1]["questions"][0]["id"] = data["assessments"][0]["questions"][0]["id"]
    with pytest.raises(ValueError, match="Duplicate assessment question id"):
        validate_skill_assessments(data)


def test_invalid_correct_option_id_is_rejected():
    data = copy.deepcopy(catalog())
    data["assessments"][0]["questions"][0]["correct_option_id"] = "missing-option"
    with pytest.raises(ValueError, match="correct_option_id does not match"):
        validate_skill_assessments(data)


def test_exact_case_insensitive_and_alias_matching():
    data = catalog()
    assert find_skill_assessment("  FASTAPI ", data)["skill"] == "FastAPI"
    assert find_skill_assessment("containers", data)["skill"] == "Docker"
    assert find_skill_assessment("RESTFUL API", data)["skill"] == "REST APIs"


def test_selects_at_most_two_missing_required_skills_in_order():
    selected = select_assessment_skills(["Docker", "FastAPI", "SQL"], catalog(), max_skills=99)
    assert [item["skill"] for item in selected] == ["Docker", "FastAPI"]
    assert all(item["assessment"] for item in selected)


def test_available_assessments_use_slots_before_fallbacks():
    selected = select_assessment_skills(["FastAPI", "PostgreSQL", "Docker"], catalog())
    assert [item["skill"] for item in selected] == ["FastAPI", "Docker"]
    assert all(item["assessment"] for item in selected)


def _answers_for_correct_count(assessment, count):
    answers = {}
    for index, question in enumerate(assessment["questions"][:3]):
        if index < count:
            answers[question["id"]] = question["correct_option_id"]
        else:
            answers[question["id"]] = next(
                option["id"] for option in question["options"] if option["id"] != question["correct_option_id"]
            )
    return answers


@pytest.mark.parametrize(
    ("correct_count", "percentage", "passed"),
    [(0, 0, False), (1, 33, False), (2, 67, True), (3, 100, True)],
)
def test_three_question_scoring(correct_count, percentage, passed):
    data = catalog()
    assessment = find_skill_assessment("Docker", data)
    result = calculate_assessment_result(
        assessment,
        _answers_for_correct_count(assessment, correct_count),
        data["assessment_rules"]["passing_score_percentage"],
    )
    assert result["correct_answers"] == correct_count
    assert result["total_questions"] == 3
    assert result["score_percentage"] == percentage
    assert result["passed"] is passed


def test_question_selection_is_exactly_three_and_deterministic():
    data = catalog()
    assessment = find_skill_assessment("Docker", data)
    first = assessment_questions(assessment, data)
    second = assessment_questions(assessment, data)
    assert len(first) == 3
    assert [question["id"] for question in first] == [question["id"] for question in second]


def test_arabic_and_english_result_content_includes_note_and_corrections():
    data = catalog()
    assessment = find_skill_assessment("Docker", data)
    result = calculate_assessment_result(assessment, _answers_for_correct_count(assessment, 2), 67)
    english = assessment_result_html(result, data, "en", "roadmap-job-docker")
    arabic = assessment_result_html(result, data, "mixed", "roadmap-job-docker")
    assert "Score" in english and "Correct answer" in english and "Explanation" in english
    assert "This is a preliminary demo assessment, not a professional certification." in english
    assert 'dir="ltr"' in english
    assert "النتيجة" in arabic and "الإجابة الصحيحة" in arabic and "التوضيح" in arabic
    assert "هذا تقييم أولي للديمو، وليس شهادة مهنية." in arabic
    assert 'dir="rtl"' in arabic


def test_missing_assessment_uses_catalog_fallback():
    data = catalog()
    selected = select_assessment_skills(["Unknown Skill"], data)
    assert selected[0]["assessment"] is None
    assert data["fallback"]["ar"]
    assert data["fallback"]["en"]
