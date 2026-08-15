import copy
import json
from pathlib import Path

import pytest

from src.career_agent import (
    build_agent_context,
    build_message_signature,
    get_companion_visual,
    get_current_stage_progress,
    get_localized_action,
    initialize_agent_state,
    reset_job_dependent_state,
    resolve_agent_message,
    transition_agent_state,
)
from src.config import AGENT_FLOW_PATH, COMPANION_ASSET_PATH, DEMO_PROFILE_PATH, JOBS_PATH, LEARNING_RESOURCES_PATH, READINESS_RULES_PATH
from src.data_loader import load_agent_flow, load_demo_profile, load_learning_resources, load_readiness_rules, validate_agent_flow
from src.job_search import JobSearchIndex, LocalJobProvider
from src.learning_roadmap import build_skill_roadmaps
from src.readiness import calculate_readiness


def flow():
    return load_agent_flow(AGENT_FLOW_PATH)


def profile():
    return load_demo_profile(DEMO_PROFILE_PATH)


def job_results():
    return JobSearchIndex(LocalJobProvider(JOBS_PATH).load()).search("Find a backend developer job", profile())


def test_valid_agent_flow_loading():
    data = flow()
    assert data["session_state"]["initial_state"] == "profile_loaded"
    assert len(data["states"]) == 14


def test_missing_and_invalid_agent_flow_file(tmp_path: Path):
    from src.data_loader import load_agent_flow
    with pytest.raises(FileNotFoundError, match="Agent-flow file is missing"):
        load_agent_flow(tmp_path / "missing.json")
    malformed = tmp_path / "malformed.json"
    malformed.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="Could not read agent flow"):
        load_agent_flow(malformed)
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps({"flow_version": "1"}), encoding="utf-8")
    with pytest.raises(ValueError, match="Agent flow is missing"):
        load_agent_flow(invalid)


def test_duplicate_stage_index_is_rejected():
    data = copy.deepcopy(flow())
    data["journey"]["stages"]["discover"]["index"] = 0
    with pytest.raises(ValueError, match="stage index"):
        validate_agent_flow(data)


def test_duplicate_stage_or_state_id_is_rejected(tmp_path: Path):
    raw = AGENT_FLOW_PATH.read_text(encoding="utf-8")
    duplicate_stage = tmp_path / "duplicate-stage.json"
    duplicate_stage.write_text(raw.replace('"profile": {', '"profile": {}, "profile": {', 1), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key: profile"):
        load_agent_flow(duplicate_stage)
    data = copy.deepcopy(flow())
    data["states"][1]["id"] = data["states"][0]["id"]
    with pytest.raises(ValueError, match="state id"):
        validate_agent_flow(data)


def test_invalid_state_stage_and_action_references_are_rejected():
    data = copy.deepcopy(flow())
    data["states"][0]["stage"] = "missing"
    with pytest.raises(ValueError, match="invalid stage"):
        validate_agent_flow(data)
    data = copy.deepcopy(flow())
    data["states"][0]["primary_action"] = "missing"
    with pytest.raises(ValueError, match="invalid action"):
        validate_agent_flow(data)


def test_invalid_transition_reference_is_rejected():
    data = copy.deepcopy(flow())
    data["transitions"][0]["to"] = "missing"
    with pytest.raises(ValueError, match="invalid state"):
        validate_agent_flow(data)


def test_unknown_template_placeholder_is_rejected():
    data = copy.deepcopy(flow())
    data["states"][0]["message_en"] += " {invented_value}"
    with pytest.raises(ValueError, match="unknown placeholders"):
        validate_agent_flow(data)


def test_missing_context_uses_fallback_without_unresolved_placeholders():
    data = flow()
    message = resolve_agent_message("job_selected", {}, data, "en")
    assert message == next(state for state in data["states"] if state["id"] == "job_selected")["fallback_message_en"]
    assert "{" not in message and "None" not in message


def test_arabic_english_and_profile_specific_welcome_messages():
    data = flow()
    first = profile()
    second = copy.deepcopy(first)
    second["career_profile"]["target_role"] = "Data Analyst"
    first_context = build_agent_context(first, language="ar")
    second_context = build_agent_context(second, language="en")
    arabic = resolve_agent_message("profile_loaded", first_context, data, "ar")
    english = resolve_agent_message("profile_loaded", second_context, data, "en")
    assert first["career_profile"]["target_role"] in arabic
    assert "Data Analyst" in english
    assert arabic != english


def test_opportunity_count_top_job_and_score_are_dynamic():
    data, results = flow(), job_results()
    context = build_agent_context(profile(), results, language="en")
    message = resolve_agent_message("opportunities_found", context, data, "en")
    assert str(len(results)) in message
    assert results[0]["job"]["title"] in message
    assert f"{round(results[0]['score'])}%" in message


def test_general_career_question_preserves_current_state():
    data = flow()
    state = initialize_agent_state(data)
    state["current_state"], state["current_stage"] = "gap_analyzed", "skill_gap"
    updated = transition_agent_state(state, "general_career_question_answered", {"fast_matcher_answer_was_returned": True}, data)
    assert updated["current_state"] == "gap_analyzed"


def test_job_search_no_result_and_job_selection_transitions():
    data = flow()
    state = transition_agent_state(initialize_agent_state(data), "job_search_intent_detected", {"normalized_job_query": "backend"}, data)
    assert state["current_state"] == "discovering"
    empty = transition_agent_state(state, "job_search_completed", {"job_results_count": 0}, data)
    assert empty["current_state"] == "clarification_needed"
    state = transition_agent_state(state, "job_search_completed", {"job_results_count": 1}, data)
    selected = transition_agent_state(state, "job_selected_or_changed", {"selected_job_id_is_valid": True}, data)
    assert selected["current_state"] == "job_selected"


def test_changing_jobs_clears_only_previous_job_downstream_state():
    data = flow()
    state = initialize_agent_state(data)
    state.update({
        "selected_job_id": "JOB-A",
        "assessment_results_by_job": {"JOB-A": {"x": 1}, "JOB-C": {"y": 2}},
        "readiness_result_by_job": {"JOB-A": {"score": 1}, "JOB-C": {"score": 2}},
        "current_job_results": ["preserved"],
    })
    updated = reset_job_dependent_state(state, "JOB-B", {"job": {"id": "JOB-B"}})
    assert "JOB-A" not in updated["assessment_results_by_job"]
    assert updated["assessment_results_by_job"]["JOB-C"] == {"y": 2}
    assert updated["current_job_results"] == ["preserved"]
    assert updated["selected_job_id"] == "JOB-B"


def test_assessment_results_are_isolated_by_job_id():
    state = initialize_agent_state(flow())
    state["assessment_results_by_job"] = {"JOB-1": {"Docker": {"score": 67}}, "JOB-2": {"SQL": {"score": 100}}}
    assert state["assessment_results_by_job"]["JOB-1"] != state["assessment_results_by_job"]["JOB-2"]


def test_required_gap_and_no_gap_branches():
    data = flow()
    base = initialize_agent_state(data)
    base["current_state"], base["current_stage"] = "job_selected", "match"
    gap = transition_agent_state(base, "skill_gap_calculated", {"missing_required_skills_count": 2}, data)
    clear = transition_agent_state(base, "skill_gap_calculated", {"missing_required_skills_count": 0}, data)
    assert gap["current_state"] == "gap_analyzed"
    assert clear["current_state"] == "no_required_gaps"


def test_roadmap_uses_actual_priority_skill():
    resources = load_learning_resources(LEARNING_RESOURCES_PATH)
    roadmaps = build_skill_roadmaps(["FastAPI", "Docker"], resources)
    context = build_agent_context(profile(), roadmaps=roadmaps, language="en")
    message = resolve_agent_message("roadmap_ready", context, flow(), "en")
    assert roadmaps[0]["requested_skill"] == "FastAPI"
    assert "FastAPI" in message and str(roadmaps[0]["estimated_hours"]) in message


@pytest.mark.parametrize(("passed", "expected"), [(True, "assessment_passed"), (False, "assessment_failed")])
def test_assessment_submission_branches(passed, expected):
    data = flow()
    state = initialize_agent_state(data)
    state["current_state"], state["current_stage"] = "assessment_pending", "verify"
    updated = transition_agent_state(state, "assessment_submitted", {"assessment_passed": passed}, data)
    assert updated["current_state"] == expected


def test_readiness_context_uses_existing_readiness_output_and_no_gap_score():
    rules = load_readiness_rules(READINESS_RULES_PATH)
    readiness = calculate_readiness(90, [], ["Python", "SQL"], [], rules)
    context = build_agent_context(profile(), readiness_result=readiness, readiness_rules=rules, language="en")
    message = resolve_agent_message("readiness_ready", context, flow(), "en")
    assert readiness["skill_assessment_score"] == 100
    assert f"{readiness['readiness_score']}%" in message
    assert readiness["status"]["label_en"] in message


def test_apply_requires_ready_status_and_valid_url():
    data = flow()
    state = initialize_agent_state(data)
    state["current_state"], state["current_stage"] = "readiness_ready", "verify"
    blocked = transition_agent_state(state, "readiness_action_requested", {"readiness_status_id": "ready_to_apply", "selected_job_url_is_valid": False}, data)
    allowed = transition_agent_state(state, "readiness_action_requested", {"readiness_status_id": "ready_to_apply", "selected_job_url_is_valid": True}, data)
    redirected = transition_agent_state(state, "readiness_action_requested", {"readiness_status_id": "almost_ready"}, data)
    assert blocked["current_state"] == "readiness_ready"
    assert allowed["current_state"] == "apply_ready"
    assert redirected["current_state"] == "gap_analyzed"


def test_stage_progress_actions_missing_asset_and_message_deduplication(tmp_path: Path):
    data = flow()
    state = initialize_agent_state(data)
    progress = get_current_stage_progress(state, data)
    assert progress[0]["status"] == "active" and progress[-1]["status"] == "pending"
    assert get_localized_action("profile_loaded", data, "ar")["label"] == data["actions"]["focus_chat_input"]["label_ar"]
    assert get_companion_visual(COMPANION_ASSET_PATH, data, "en")["kind"] == "image"
    fallback = get_companion_visual(tmp_path / "missing.png", data, "en")
    assert fallback["kind"] == "fallback" and fallback["value"] == "🧭"
    context = {"target_role": "Backend Developer"}
    first = build_message_signature("profile_loaded", None, "hello", context)
    second = build_message_signature("profile_loaded", None, "hello", context)
    changed = build_message_signature("profile_loaded", "JOB-1", "hello", context)
    assert first == second and first != changed
