"""Deterministic selection and scoring for static skill assessments."""
from __future__ import annotations

from typing import Any

from src.job_search import normalize_skill


def find_skill_assessment(skill_name: str, catalog: dict[str, Any]) -> dict[str, Any] | None:
    """Match a missing skill against normalized assessment names and aliases."""
    wanted = normalize_skill(skill_name)
    for assessment in catalog.get("assessments", []):
        names = [assessment.get("skill", ""), *assessment.get("aliases", [])]
        if wanted and wanted in {normalize_skill(name) for name in names}:
            return assessment
    return None


def select_assessment_skills(
    missing_required_skills: list[str],
    catalog: dict[str, Any],
    max_skills: int | None = None,
) -> list[dict[str, Any]]:
    """Select at most two required gaps in their existing deterministic order."""
    configured = catalog.get("assessment_rules", {}).get("max_skills_per_assessment", 2)
    limit = min(max_skills if max_skills is not None else configured, configured, 2)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for skill_name in missing_required_skills:
        normalized = normalize_skill(skill_name)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        candidates.append({"skill": skill_name, "assessment": find_skill_assessment(skill_name, catalog)})
    # Preserve required-gap order within each group, but use scarce demo slots
    # for assessable skills before showing a no-assessment fallback.
    candidates.sort(key=lambda item: item["assessment"] is None)
    return candidates[:max(0, limit)]


def assessment_questions(assessment: dict[str, Any], catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the configured leading questions without shuffling."""
    count = catalog["assessment_rules"]["questions_per_skill"]
    return assessment["questions"][:count]


def calculate_assessment_result(
    assessment: dict[str, Any],
    answers: dict[str, str | None],
    passing_score_percentage: int | float,
    questions_per_skill: int = 3,
) -> dict[str, Any]:
    """Score one skill independently; unanswered questions count as incorrect."""
    questions = assessment["questions"][:questions_per_skill]
    details: list[dict[str, Any]] = []
    correct_answers = 0
    for question in questions:
        selected = answers.get(question["id"])
        is_correct = selected == question["correct_option_id"]
        correct_answers += int(is_correct)
        details.append({
            "question": question,
            "selected_option_id": selected,
            "correct_option_id": question["correct_option_id"],
            "is_correct": is_correct,
        })
    total = len(questions)
    percentage = round((correct_answers / total) * 100) if total else 0
    return {
        "skill": assessment["skill"],
        "correct_answers": correct_answers,
        "total_questions": total,
        "score_percentage": percentage,
        "passed": percentage >= passing_score_percentage,
        "details": details,
    }
