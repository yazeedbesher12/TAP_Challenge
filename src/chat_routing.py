"""Pure deterministic routing for short UI-like chat fragments."""
from __future__ import annotations

import re
from typing import Any

from src.fast_matcher import normalize_text


def _compact(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9+#./-]+|[\u0621-\u064A]+", normalize_text(text), re.IGNORECASE))


def find_typed_assessment_option(message: str, catalog: dict[str, Any]) -> dict[str, Any] | None:
    """Recognize an assessment option pasted into chat without scoring it."""
    wanted = _compact(message)
    if not wanted:
        return None
    for assessment in catalog.get("assessments", []):
        for question in assessment.get("questions", []):
            for option in question.get("options", []):
                if wanted in {_compact(option.get("ar", "")), _compact(option.get("en", ""))}:
                    return {"skill": assessment["skill"], "question_id": question["id"]}
    return None


def is_roadmap_ui_request(message: str) -> bool:
    value = _compact(message)
    phrases = {
        _compact("خطة قصيرة لسد فجوة المهارات"),
        _compact("خطة سد فجوة المهارات"),
        _compact("Mini Skill-Gap Roadmap"),
        _compact("learning roadmap"),
    }
    return value in phrases


def find_role_fragment(message: str, jobs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Recognize a short role-only reply while avoiding full questions."""
    value = _compact(message)
    if not value or len(value.split()) > 6 or any(mark in message for mark in ("?", "؟")):
        return None
    for job in jobs:
        role_names = [job.get("title", ""), job.get("title_ar", ""), *job.get("aliases", [])]
        if any((role := _compact(name)) and role in value for name in role_names):
            return job
    return None
