import copy
import json
from pathlib import Path

import pytest

from app import readiness_card_html
from src.config import READINESS_RULES_PATH
from src.data_loader import load_readiness_rules, validate_readiness_rules
from src.readiness import calculate_readiness


def rules():
    return load_readiness_rules(READINESS_RULES_PATH)


def assessment(skill, percentage, passed=True):
    return {"skill": skill, "score_percentage": percentage, "passed": passed}


def test_valid_readiness_rules_loading():
    data = rules()
    assert sum(data["score"]["weights"].values()) == 1.0
    assert {status["id"] for status in data["statuses"]} >= {
        "ready_to_apply", "almost_ready", "needs_preparation", "assessment_required"
    }


def test_missing_and_invalid_readiness_rules_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Readiness-rules file is missing"):
        load_readiness_rules(tmp_path / "missing.json")
    malformed = tmp_path / "malformed.json"
    malformed.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="Could not read readiness rules"):
        load_readiness_rules(malformed)
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps({"score": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="Readiness rules are missing"):
        load_readiness_rules(invalid)


def test_weight_sum_validation():
    data = copy.deepcopy(rules())
    data["score"]["weights"]["job_match_score"] = 0.7
    with pytest.raises(ValueError, match="sum to 1.0"):
        validate_readiness_rules(data)


def test_status_ranges_must_cover_zero_through_one_hundred():
    data = copy.deepcopy(rules())
    next(status for status in data["statuses"] if status["id"] == "ready_to_apply")["minimum_score"] = 81
    with pytest.raises(ValueError, match="cover every score"):
        validate_readiness_rules(data)


def test_invalid_gate_status_reference_is_rejected():
    data = copy.deepcopy(rules())
    data["gates"][1]["maximum_status"] = "unknown_status"
    with pytest.raises(ValueError, match="references unknown status"):
        validate_readiness_rules(data)


def test_formula_uses_weights_from_rules():
    result = calculate_readiness(80, ["Docker"], ["Python"], [assessment("Docker", 50)], rules())
    assert result["readiness_score"] == round(80 * 0.6 + 50 * 0.4) == 68


@pytest.mark.parametrize(
    ("job_score", "skill_score", "status_id"),
    [(90, 90, "ready_to_apply"), (70, 70, "almost_ready"), (50, 50, "needs_preparation")],
)
def test_score_threshold_statuses(job_score, skill_score, status_id):
    result = calculate_readiness(job_score, ["Docker"], [], [assessment("Docker", skill_score)], rules())
    assert result["status_id"] == status_id


def test_no_missing_skills_uses_assessment_score_one_hundred():
    result = calculate_readiness(80, [], ["Python", "SQL"], [assessment("Unrelated", 0, False)], rules())
    assert result["skill_assessment_score"] == 100
    assert result["readiness_score"] == 88
    assert result["status_id"] == "ready_to_apply"


def test_missing_skills_without_completed_assessment_requires_assessment():
    result = calculate_readiness(90, ["Docker"], ["Python"], [], rules())
    assert result["state"] == "assessment_required"
    assert result["readiness_score"] is None
    assert result["status_id"] == "assessment_required"


def test_failed_required_assessment_caps_ready_score_at_almost_ready():
    result = calculate_readiness(100, ["Docker"], ["Python"], [assessment("Docker", 67, False)], rules())
    assert result["readiness_score"] == 87
    assert result["status_id"] == "almost_ready"
    assert [gate["id"] for gate in result["applied_gates"]] == ["failed_required_skill_caps_readiness"]


def test_triggered_failed_gate_remains_explained_when_score_is_already_lower():
    result = calculate_readiness(50, ["Docker"], [], [assessment("Docker", 33, False)], rules())
    assert result["status_id"] == "needs_preparation"
    assert [gate["id"] for gate in result["applied_gates"]] == ["failed_required_skill_caps_readiness"]


def test_three_missing_required_skills_cap_at_needs_preparation():
    result = calculate_readiness(
        100,
        ["Docker", "FastAPI", "PostgreSQL"],
        ["Python"],
        [assessment("Docker", 100)],
        rules(),
    )
    assert result["readiness_score"] == 100
    assert result["status_id"] == "needs_preparation"
    assert result["applied_gates"][-1]["id"] == "many_required_gaps_need_preparation"


def test_unrelated_assessments_are_ignored():
    result = calculate_readiness(90, ["Docker"], [], [assessment("SQL", 100)], rules())
    assert result["status_id"] == "assessment_required"
    assert result["readiness_score"] is None


def test_strength_and_gap_display_limits():
    result = calculate_readiness(
        70,
        ["One", "Two", "Three", "Four"],
        ["A", "B", "C", "D"],
        [assessment("One", 70)],
        rules(),
    )
    assert result["strengths"] == ["A", "B", "C"]
    assert result["priority_gaps"] == ["One", "Two", "Three"]


def test_missing_job_returns_empty_state():
    result = calculate_readiness(None, [], [], [], rules())
    assert result["state"] == "missing_job_match"
    assert result["readiness_score"] is None


def test_arabic_and_english_readiness_labels_and_disclaimer():
    data = rules()
    result = calculate_readiness(90, [], ["Python"], [], data)
    job = {"apply_url": "https://jobs.tap.example/apply"}
    english = readiness_card_html(result, job, data, "en", "roadmap", "assessment")
    arabic = readiness_card_html(result, job, data, "mixed", "roadmap", "assessment")
    assert "Final" not in english  # The expander owns the section title.
    assert "Ready to Apply" in english and "60% Job Match + 40% Skill Assessment" in english
    assert "not a hiring guarantee" in english and 'dir="ltr"' in english
    assert "جاهز للتقديم" in arabic and "60% مطابقة الوظيفة + 40% اختبار المهارات" in arabic
    assert "ليست ضماناً للتوظيف" in arabic and 'dir="rtl"' in arabic
