"""Pure deterministic Final Job Readiness calculation."""
from __future__ import annotations

from typing import Any, Iterable

from src.job_search import normalize_skill


def _status_by_id(rules: dict[str, Any], status_id: str) -> dict[str, Any]:
    return next(status for status in rules["statuses"] if status["id"] == status_id)


def _score_status(rules: dict[str, Any], score: int) -> dict[str, Any]:
    return next(
        status for status in rules["statuses"]
        if status.get("minimum_score") is not None and status["minimum_score"] <= score <= status["maximum_score"]
    )


def _assessment_values(assessment_results: Iterable[dict[str, Any]] | dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return list(assessment_results.values()) if isinstance(assessment_results, dict) else list(assessment_results)


def calculate_readiness(
    job_match_score: float | int | None,
    missing_required_skills: list[str],
    matched_skills: list[str],
    assessment_results: Iterable[dict[str, Any]] | dict[str, dict[str, Any]],
    rules: dict[str, Any],
) -> dict[str, Any]:
    """Calculate readiness from one existing job result and session-only assessments."""
    limits = rules["display"]
    if job_match_score is None:
        return {
            "state": "missing_job_match",
            "status_id": None,
            "readiness_score": None,
            "message": rules["empty_states"]["missing_job_match"],
            "strengths": matched_skills[:limits["max_strengths"]],
            "priority_gaps": missing_required_skills[:limits["max_gaps"]],
        }
    missing_names = {normalize_skill(skill) for skill in missing_required_skills}
    relevant_results = [
        result for result in _assessment_values(assessment_results)
        if normalize_skill(str(result.get("skill", ""))) in missing_names
        and isinstance(result.get("score_percentage"), (int, float))
    ]
    if missing_required_skills and not relevant_results:
        status = _status_by_id(rules, "assessment_required")
        return {
            "state": "assessment_required",
            "status_id": status["id"],
            "status": status,
            "readiness_score": None,
            "job_match_score": max(0, min(100, round(job_match_score))),
            "skill_assessment_score": None,
            "strengths": matched_skills[:limits["max_strengths"]],
            "priority_gaps": missing_required_skills[:limits["max_gaps"]],
            "applied_gates": [],
            "action": rules["actions"][status["primary_action"]],
            "disclaimer": rules["disclaimer"],
        }
    skill_score = 100 if not missing_required_skills else round(
        sum(result["score_percentage"] for result in relevant_results) / len(relevant_results)
    )
    bounded_job_score = max(0, min(100, round(job_match_score)))
    weights = rules["score"]["weights"]
    readiness_score = round(
        bounded_job_score * weights["job_match_score"]
        + skill_score * weights["skill_assessment_score"]
    )
    status = _score_status(rules, readiness_score)
    failed_count = sum(not bool(result.get("passed")) for result in relevant_results)
    applied_gates: list[dict[str, Any]] = []
    facts = {
        "failed_required_skill_caps_readiness": failed_count > 0,
        "many_required_gaps_need_preparation": len(missing_required_skills) >= 3,
    }
    for gate in sorted(rules["gates"], key=lambda item: item["priority"]):
        if gate.get("effect") != "cap_status" or not facts.get(gate.get("id"), False):
            continue
        cap = _status_by_id(rules, gate["maximum_status"])
        # A triggered gate is still useful explanatory evidence when the score
        # already produced an equal or lower status.
        applied_gates.append(gate)
        if status["rank"] > cap["rank"]:
            status = cap
    return {
        "state": "calculated",
        "status_id": status["id"],
        "status": status,
        "readiness_score": readiness_score,
        "job_match_score": bounded_job_score,
        "skill_assessment_score": skill_score,
        "strengths": matched_skills[:limits["max_strengths"]],
        "priority_gaps": missing_required_skills[:limits["max_gaps"]],
        "applied_gates": applied_gates,
        "action": rules["actions"][status["primary_action"]],
        "weights": weights,
        "disclaimer": rules["disclaimer"],
    }
