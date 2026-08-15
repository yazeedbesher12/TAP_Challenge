import hashlib

from app import match_label, next_action_text
from src.config import DEMO_PROFILE_PATH, JOBS_PATH, KB_PATH
from src.data_loader import load_demo_profile, load_knowledge_base
from src.job_search import (
    JobSearchIndex,
    LocalJobProvider,
    analyze_skill_gap,
    classify_match,
    normalize_skill,
)


def profile(**career_overrides):
    career = {"target_role": "Backend Developer", "experience_level": "entry_level"}
    career.update(career_overrides)
    return {"career_profile": career, "skills": ["Python", "Flask", "SQL", "Git", "REST APIs"]}


def job(title="Backend Developer", skills=None, **overrides):
    value = {
        "title": title,
        "title_ar": title,
        "aliases": [title],
        "skills": skills if skills is not None else ["Python", "Flask", "SQL", "REST APIs"],
        "experience_level": "Junior",
        "status": "active",
    }
    value.update(overrides)
    return value


def test_skill_normalization_is_case_insensitive_and_handles_aliases_and_punctuation():
    assert normalize_skill("  PYTHON  ") == "python"
    assert normalize_skill("REST-API") == "rest apis"
    assert normalize_skill(" React_JS ") == "react"
    assert normalize_skill("nodejs") == "node.js"
    assert normalize_skill("Docker   Containers") == "docker"


def test_related_but_different_technologies_remain_distinct():
    candidate = ["GitHub", "SQL", "Flask"]
    gap = analyze_skill_gap(candidate, job(skills=["Git", "PostgreSQL", "FastAPI"]))
    assert gap["matched_required_skills"] == []
    assert gap["missing_required_skills"] == ["Git", "PostgreSQL", "FastAPI"]


def test_all_required_skills_produce_highly_suitable():
    candidate = profile()
    role = job()
    gap = analyze_skill_gap(candidate["skills"], role)
    assert gap["required_match_ratio"] == 1.0
    assert classify_match(role, candidate, gap) == "highly_suitable"


def test_one_missing_skill_at_eighty_percent_produces_small_gap():
    candidate = profile()
    role = job(skills=["Python", "Flask", "SQL", "REST APIs", "Docker"])
    gap = analyze_skill_gap(candidate["skills"], role)
    assert gap["missing_required_skills"] == ["Docker"]
    assert gap["required_match_ratio"] == 0.8
    assert classify_match(role, candidate, gap) == "suitable_small_gap"


def test_related_role_with_two_shared_skills_is_related_opportunity():
    candidate = profile(bridge_role="Data Engineer")
    role = job("Junior Data Analyst", ["Python", "SQL", "Power BI", "Excel", "Data Visualization"])
    gap = analyze_skill_gap(candidate["skills"], role)
    assert classify_match(role, candidate, gap) == "related_opportunity"


def test_unrelated_role_and_senior_role_are_excluded():
    candidate = profile()
    mobile = job("Flutter Developer", ["Git", "REST APIs", "Flutter", "Dart"])
    senior = job("Senior Backend Developer", ["Python"], experience_level="Senior")
    assert classify_match(mobile, candidate, analyze_skill_gap(candidate["skills"], mobile)) == "exclude"
    assert classify_match(senior, candidate, analyze_skill_gap(candidate["skills"], senior)) == "exclude"


def test_nice_to_have_and_missing_optional_fields_are_safe():
    candidate = profile()
    with_optional = job(nice_to_have_skills=["Docker"])
    gap = analyze_skill_gap(candidate["skills"], with_optional)
    assert gap["missing_nice_to_have_skills"] == ["Docker"]
    assert classify_match(with_optional, candidate, gap) == "highly_suitable"

    minimal = job()
    minimal.pop("skills")
    empty_gap = analyze_skill_gap(candidate["skills"], minimal)
    assert empty_gap["required_match_ratio"] == 1.0
    assert empty_gap["missing_nice_to_have_skills"] == []


def test_search_returns_at_most_three_deterministic_results():
    index = JobSearchIndex(LocalJobProvider(JOBS_PATH).load())
    candidate = load_demo_profile(DEMO_PROFILE_PATH)
    first = index.search("Find a job", candidate, top_k=99)
    second = index.search("Find a job", candidate, top_k=99)
    assert len(first) <= 3
    assert [item["job"]["id"] for item in first] == [item["job"]["id"] for item in second]


def test_bilingual_labels_and_next_actions_use_structured_key():
    result = {"match_label_key": "suitable_small_gap", "next_action_key": "suitable_small_gap", "missing_required_skills": ["Docker"]}
    assert match_label(result["match_label_key"], False) == "⭐ Suitable with a small gap"
    assert match_label(result["match_label_key"], True) == "⭐ مناسبة مع فجوة بسيطة"
    assert "Docker" in next_action_text(result, False)
    assert "Docker" in next_action_text(result, True)


def test_knowledge_base_validation_is_read_only():
    before = hashlib.sha256(KB_PATH.read_bytes()).hexdigest()
    knowledge_base = load_knowledge_base(KB_PATH)
    after = hashlib.sha256(KB_PATH.read_bytes()).hexdigest()
    assert knowledge_base["items"]
    assert before == after
