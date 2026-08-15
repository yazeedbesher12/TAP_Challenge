"""Pure state and template engine for the deterministic TAP Companion."""
from __future__ import annotations

import copy
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any, Iterable


def _states(flow: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {state["id"]: state for state in flow["states"]}


def initialize_agent_state(flow: dict[str, Any]) -> dict[str, Any]:
    initial = flow["session_state"]["initial_state"]
    initial_definition = _states(flow)[initial]
    return {
        "current_state": initial,
        "current_stage": initial_definition["stage"],
        "current_job_results": [],
        "selected_job_id": None,
        "selected_job_match": None,
        "skill_gap": None,
        "selected_roadmaps": [],
        "latest_assessment": None,
        "assessment_results_by_job": {},
        "readiness_result_by_job": {},
        "last_agent_message_signature": None,
    }


def reset_job_dependent_state(
    agent_state: dict[str, Any],
    new_job_id: str,
    selected_match: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Change jobs while preserving profile/chat and isolating job-specific work."""
    updated = copy.deepcopy(agent_state)
    previous = updated.get("selected_job_id")
    if previous and previous != new_job_id:
        updated.get("assessment_results_by_job", {}).pop(previous, None)
        updated.get("readiness_result_by_job", {}).pop(previous, None)
    updated["selected_job_id"] = new_job_id
    updated["selected_job_match"] = selected_match
    updated["skill_gap"] = None
    updated["selected_roadmaps"] = []
    updated["latest_assessment"] = None
    return updated


def build_agent_context(
    profile: dict[str, Any] | None,
    job_results: list[dict[str, Any]] | None = None,
    selected_match: dict[str, Any] | None = None,
    roadmaps: list[dict[str, Any]] | None = None,
    latest_assessment: dict[str, Any] | None = None,
    readiness_result: dict[str, Any] | None = None,
    readiness_rules: dict[str, Any] | None = None,
    language: str = "en",
) -> dict[str, Any]:
    """Map existing project structures explicitly; JSON source strings are never evaluated."""
    arabic = language in {"ar", "mixed"}
    career = profile.get("career_profile", {}) if profile else {}
    preferences = profile.get("work_preferences", {}) if profile else {}
    results = job_results or []
    top = results[0] if results else None
    selected_job = selected_match.get("job", {}) if selected_match else {}
    top_job = top.get("job", {}) if top else {}
    roadmap = (roadmaps or [None])[0]
    status = readiness_result.get("status", {}) if readiness_result else {}
    action = readiness_result.get("action", {}) if readiness_result else {}
    suffix = "ar" if arabic else "en"
    return {
        "target_role": career.get("target_role"),
        "top_skills": profile.get("skills", []) if profile else [],
        "preferred_work_type": preferences.get("preferred_modes", []),
        "jobs_count": len(results),
        "top_job_title": top_job.get("title_ar" if arabic else "title"),
        "top_job_match_score": top.get("score") if top else None,
        "selected_job_title": selected_job.get("title_ar" if arabic else "title"),
        "selected_company": selected_job.get("company"),
        "job_match_score": selected_match.get("score") if selected_match else None,
        "matched_skills": selected_match.get("matched_required_skills", []) if selected_match else [],
        "missing_required_skills": selected_match.get("missing_required_skills", []) if selected_match else [],
        "priority_skill": (
            roadmap.get("requested_skill", roadmap.get("skill"))
            if roadmap
            else ((selected_match.get("missing_required_skills") or [None])[0] if selected_match else None)
        ),
        "roadmap_hours": roadmap.get("estimated_hours") if roadmap else None,
        "assessment_skill": latest_assessment.get("skill") if latest_assessment else None,
        "assessment_correct": latest_assessment.get("correct_answers") if latest_assessment else None,
        "assessment_total": latest_assessment.get("total_questions") if latest_assessment else None,
        "assessment_percentage": latest_assessment.get("score_percentage") if latest_assessment else None,
        "readiness_score": readiness_result.get("readiness_score") if readiness_result else None,
        "readiness_status": status.get(f"label_{suffix}"),
        "next_action": action.get(f"label_{suffix}"),
    }


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() != "none"
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _format_value(name: str, value: Any, flow: dict[str, Any], language: str) -> str | None:
    if not _has_value(value):
        return None
    binding = flow["context_bindings"].get(name, {})
    formatter = binding.get("formatter", "safe_text")
    limit = binding.get("limit")
    runtime = flow["runtime_rules"]
    if name in {"top_skills", "matched_skills"}:
        limit = min(limit or runtime["max_displayed_strengths"], runtime["max_displayed_strengths"])
    elif name == "missing_required_skills":
        limit = min(limit or runtime["max_displayed_gaps"], runtime["max_displayed_gaps"])
    if formatter == "localized_list":
        if not isinstance(value, (list, tuple)) or not value:
            return None
        separator = "، " if language in {"ar", "mixed"} else ", "
        return separator.join(html.escape(str(item)) for item in list(value)[:limit])
    if formatter == "percentage":
        if not isinstance(value, (int, float)):
            return None
        return f"{max(0, min(100, round(value)))}%"
    if formatter == "integer":
        if not isinstance(value, (int, float)):
            return None
        return str(round(value))
    if isinstance(value, (str, int, float)):
        return html.escape(str(value))
    return None


def resolve_agent_message(state_id: str, context: dict[str, Any], flow: dict[str, Any], language: str) -> str:
    """Safely render one localized state template or its localized fallback."""
    state = _states(flow)[state_id]
    suffix = "ar" if language in {"ar", "mixed"} else "en"
    formatted: dict[str, str] = {}
    fallback = html.escape(state[f"fallback_message_{suffix}"])
    for name in state["required_context"]:
        value = _format_value(name, context.get(name), flow, language)
        if value is None:
            return fallback
        formatted[name] = value
    template = html.escape(state[f"message_{suffix}"])
    try:
        rendered = template.format_map(formatted)
    except (KeyError, ValueError):
        return fallback
    if re.search(flow["template_policy"]["placeholder_pattern"], rendered) or "{" in rendered or "}" in rendered:
        return fallback
    return rendered


def _condition_matches(condition: str, facts: dict[str, Any]) -> bool:
    """Evaluate only the finite supported vocabulary; never execute JSON text."""
    checks = {
        "normalized_job_query_is_not_empty": bool(facts.get("normalized_job_query")),
        "job_results_count > 0": facts.get("job_results_count", 0) > 0,
        "job_results_count == 0": facts.get("job_results_count", 0) == 0,
        "selected_job_id_is_valid": bool(facts.get("selected_job_id_is_valid")),
        "missing_required_skills_count > 0": facts.get("missing_required_skills_count", 0) > 0,
        "missing_required_skills_count == 0": facts.get("missing_required_skills_count", 0) == 0,
        "roadmap_or_generic_fallback_is_available": bool(facts.get("roadmap_available")),
        "assessment_for_priority_skill_is_available": bool(facts.get("assessment_available")),
        "assessment_passed == true": facts.get("assessment_passed") is True,
        "assessment_passed == false": facts.get("assessment_passed") is False,
        "readiness_result_is_valid": bool(facts.get("readiness_result_is_valid")),
        "readiness_status_id == 'ready_to_apply' and selected_job_url_is_valid": facts.get("readiness_status_id") == "ready_to_apply" and bool(facts.get("selected_job_url_is_valid")),
        "readiness_status_id in ['almost_ready', 'needs_preparation']": facts.get("readiness_status_id") in {"almost_ready", "needs_preparation"},
        "fast_matcher_answer_was_returned": bool(facts.get("fast_matcher_answer_was_returned")),
        "validated_loader_error_exists": bool(facts.get("validated_loader_error_exists")),
    }
    return checks.get(condition, False)


def transition_agent_state(
    agent_state: dict[str, Any],
    event: str,
    facts: dict[str, Any],
    flow: dict[str, Any],
) -> dict[str, Any]:
    updated = copy.deepcopy(agent_state)
    current = updated["current_state"]
    for transition in flow["transitions"]:
        if transition["event"] != event:
            continue
        if current not in transition["from"] and "$any" not in transition["from"]:
            continue
        if not _condition_matches(transition["condition"], facts):
            continue
        target = current if transition["to"] == "$same_state" else transition["to"]
        updated["current_state"] = target
        updated["current_stage"] = _states(flow)[target]["stage"]
        selected_job_before_reset = updated.get("selected_job_id")
        for reset in transition.get("reset", []):
            if reset == "selected_job":
                updated["selected_job_id"] = None
                updated["selected_job_match"] = None
                continue
            key = {
                "job_results": "current_job_results",
                "skill_gap": "skill_gap",
                "roadmaps": "selected_roadmaps",
                "assessment_results": "assessment_results_by_job",
                "latest_assessment": "latest_assessment",
                "readiness_result": "readiness_result_by_job",
            }.get(reset, reset)
            if key.endswith("_by_job"):
                mapping = dict(updated.get(key, {}))
                if selected_job_before_reset:
                    mapping.pop(selected_job_before_reset, None)
                updated[key] = mapping
            else:
                updated[key] = [] if key in {"current_job_results", "selected_roadmaps"} else None
        return updated
    return updated


def get_current_stage_progress(agent_state: dict[str, Any], flow: dict[str, Any]) -> list[dict[str, Any]]:
    active = flow["journey"]["stages"][agent_state["current_stage"]]["index"]
    return [
        {
            "id": stage_id,
            **stage,
            "status": "completed" if stage["index"] < active else ("active" if stage["index"] == active else "pending"),
        }
        for stage_id, stage in sorted(flow["journey"]["stages"].items(), key=lambda item: item[1]["index"])
    ]


def get_localized_action(state_id: str, flow: dict[str, Any], language: str) -> dict[str, str] | None:
    state = _states(flow)[state_id]
    action_id = state.get("primary_action")
    if action_id is None:
        return None
    suffix = "ar" if language in {"ar", "mixed"} else "en"
    return {"id": action_id, "label": flow["actions"][action_id][f"label_{suffix}"]}


def build_message_signature(state_id: str, selected_job_id: str | None, message: str, context: dict[str, Any]) -> str:
    serializable = {key: value for key, value in context.items() if isinstance(value, (str, int, float, bool, list, type(None)))}
    payload = json.dumps([state_id, selected_job_id, message, serializable], sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def get_companion_visual(asset_path: Path, flow: dict[str, Any], language: str) -> dict[str, str]:
    """Return the known local image or the flow-defined compass fallback."""
    if asset_path.is_file():
        return {"kind": "image", "value": str(asset_path)}
    suffix = "ar" if language in {"ar", "mixed"} else "en"
    fallback = flow["fallbacks"]["missing_agent_asset"]
    return {"kind": "fallback", "value": fallback["visual"], "label": fallback[suffix]}
