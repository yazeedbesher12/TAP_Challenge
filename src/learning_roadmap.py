"""Deterministic matching and fallback roadmaps for missing job skills."""
from __future__ import annotations

from typing import Any

from src.job_search import normalize_skill

ROADMAP_STAGES = ("learn", "build", "evaluate", "portfolio")


def find_learning_resource(skill_name: str, catalog: dict[str, Any]) -> dict[str, Any] | None:
    """Find an exact normalized skill or alias match in the static catalogue."""
    wanted = normalize_skill(skill_name)
    for resource in catalog.get("resources", []):
        names = [resource.get("skill", ""), *resource.get("aliases", [])]
        if wanted and wanted in {normalize_skill(name) for name in names}:
            return resource
    return None


def _fallback_roadmap(skill_name: str, catalog: dict[str, Any]) -> dict[str, Any]:
    fallback = catalog["fallback"]
    steps = [
        {"stage": stage, "hours": None, "ar": fallback["ar"][index], "en": fallback["en"][index]}
        for index, stage in enumerate(ROADMAP_STAGES)
    ]
    return {
        "skill": skill_name,
        "estimated_hours": fallback["estimated_hours"],
        "why_ar": fallback["warning_ar"],
        "why_en": fallback["warning_en"],
        "resource": None,
        "roadmap": steps,
        "evidence_ar": "دليل عملي قابل للمراجعة مثل رابط مشروع أو ملف أعمال يوضح استخدام المهارة.",
        "evidence_en": "Reviewable practical evidence, such as a project or portfolio link demonstrating the skill.",
        "completion_criteria": ["A working exercise demonstrates the skill", "Evidence is reviewable by another person"],
        "is_fallback": True,
    }


def build_skill_roadmaps(
    missing_required_skills: list[str],
    catalog: dict[str, Any],
    missing_nice_to_have_skills: list[str] | None = None,
    max_roadmaps: int = 2,
) -> list[dict[str, Any]]:
    """Build at most two recommendations, always selecting required gaps first."""
    limit = min(max(0, max_roadmaps), 2)
    prioritized = [(skill, True) for skill in missing_required_skills]
    prioritized.extend((skill, False) for skill in (missing_nice_to_have_skills or []))
    roadmaps: list[dict[str, Any]] = []
    seen: set[str] = set()
    for skill_name, required in prioritized:
        normalized = normalize_skill(skill_name)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        resource = find_learning_resource(skill_name, catalog)
        roadmap = dict(resource) if resource else _fallback_roadmap(skill_name, catalog)
        roadmap["requested_skill"] = skill_name
        roadmap["required_gap"] = required
        roadmap.setdefault("is_fallback", False)
        roadmaps.append(roadmap)
        if len(roadmaps) == limit:
            break
    return roadmaps
