import json
from pathlib import Path

import pytest

from src.config import DEMO_PROFILE_PATH, JOBS_PATH
from src.data_loader import load_demo_profile
from src.fast_matcher import FastMatcher
from src.job_search import JobSearchIndex, LocalJobProvider

def job_index() -> JobSearchIndex:
    return JobSearchIndex(LocalJobProvider(JOBS_PATH).load())

def test_demo_profile_loads_with_required_fields():
    profile = load_demo_profile(DEMO_PROFILE_PATH)
    assert profile["profile_type"] == "demo"
    assert profile["career_profile"]["target_role"] == "Backend Developer"
    assert "Python" in profile["skills"]

def test_missing_and_invalid_demo_profiles_have_safe_loader_errors(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_demo_profile(tmp_path / "missing.json")
    invalid = tmp_path / "invalid.json"; invalid.write_text(json.dumps({"profile_id": "x"}), encoding="utf-8")
    with pytest.raises(ValueError, match="missing fields"):
        load_demo_profile(invalid)
    assert job_index().search("Find a junior backend role in Amman", None)

def test_profile_target_role_and_skills_improve_backend_ranking():
    profile = load_demo_profile(DEMO_PROFILE_PATH)
    results = job_index().search("Find a backend developer job", profile)
    assert results[0]["job"]["id"] == "JOB-002"
    assert "FastAPI" in results[0]["missing_required_skills"]
    assert "Python" not in results[0]["missing_required_skills"]

def test_entry_level_profile_excludes_mid_level_only_roles():
    profile = load_demo_profile(DEMO_PROFILE_PATH)
    results = job_index().search("Find a job", profile)
    assert results and len(results) <= 3
    assert all(result["job"]["experience_level"] != "Mid-level" for result in results)
    assert job_index().search("Find a blockchain job", profile) == []

def test_fast_matcher_remains_independent_of_demo_profile():
    from src.config import KB_PATH
    from src.data_loader import load_knowledge_base
    match = FastMatcher(load_knowledge_base(KB_PATH)).search("How can I improve my LinkedIn headline?")
    assert match[0]["item"]["intent"] == "write_linkedin_headline"
