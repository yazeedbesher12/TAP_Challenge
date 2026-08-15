import json
from pathlib import Path

import pytest

from app import roadmap_html
from src.config import LEARNING_RESOURCES_PATH
from src.data_loader import load_learning_resources
from src.learning_roadmap import build_skill_roadmaps, find_learning_resource


def catalog():
    return load_learning_resources(LEARNING_RESOURCES_PATH)


def test_valid_learning_resources_json_loads():
    data = catalog()
    assert data["catalog_type"] == "demo"
    assert len(data["resources"]) == 10
    assert data["rules"]["open_links_automatically"] is False


def test_missing_and_invalid_learning_resource_files_fail_safely(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Learning-resources file is missing"):
        load_learning_resources(tmp_path / "missing.json")

    malformed = tmp_path / "malformed.json"
    malformed.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="Could not read learning resources"):
        load_learning_resources(malformed)

    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps({"resources": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="catalogue is missing"):
        load_learning_resources(invalid)


def test_exact_case_insensitive_and_alias_matching():
    data = catalog()
    assert find_learning_resource("fastapi", data)["skill"] == "FastAPI"
    assert find_learning_resource("  MACHINE   LEARNING ", data)["skill"] == "Machine Learning"
    assert find_learning_resource("RESTFUL API", data)["skill"] == "REST APIs"


def test_docker_roadmap_is_retrieved_through_alias():
    resource = find_learning_resource("containers", catalog())
    assert resource["skill"] == "Docker"
    assert resource["resource"]["url"] == "https://docs.docker.com/get-started/"
    assert [step["stage"] for step in resource["roadmap"]] == ["learn", "build", "evaluate", "portfolio"]


def test_unknown_skill_uses_generic_fallback_without_invented_link():
    roadmaps = build_skill_roadmaps(["Quantum Widgets"], catalog())
    assert len(roadmaps) == 1
    assert roadmaps[0]["requested_skill"] == "Quantum Widgets"
    assert roadmaps[0]["is_fallback"] is True
    assert roadmaps[0]["resource"] is None
    assert len(roadmaps[0]["roadmap"]) == 4


def test_maximum_two_roadmaps_and_required_skills_are_prioritized():
    roadmaps = build_skill_roadmaps(
        ["Docker", "FastAPI", "SQL"],
        catalog(),
        missing_nice_to_have_skills=["Pandas"],
        max_roadmaps=99,
    )
    assert [item["requested_skill"] for item in roadmaps] == ["Docker", "FastAPI"]
    assert all(item["required_gap"] for item in roadmaps)


def test_optional_gap_only_uses_remaining_capacity():
    roadmaps = build_skill_roadmaps(["Docker"], catalog(), ["Pandas", "SQL"])
    assert [item["requested_skill"] for item in roadmaps] == ["Docker", "Pandas"]
    assert [item["required_gap"] for item in roadmaps] == [True, False]


def test_roadmap_content_is_bilingual_and_link_is_clickable_only():
    roadmap = build_skill_roadmaps(["Docker"], catalog())[0]
    english = roadmap_html(roadmap, "en")
    arabic = roadmap_html(roadmap, "mixed")
    assert 'dir="ltr"' in english and "Why this skill matters" in english
    assert "Learn" in english and "Build" in english and "Evaluate" in english and "Portfolio" in english
    assert 'dir="rtl"' in arabic and "لماذا تهم هذه المهارة" in arabic
    assert "تعلّم" in arabic and "طبّق" in arabic and "قيّم" in arabic and "أضف لملف أعمالك" in arabic
    assert '<a href="https://docs.docker.com/get-started/"' in english
    assert "window.open" not in english and "script" not in english.lower()
