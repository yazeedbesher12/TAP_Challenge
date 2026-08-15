"""Safe local-only profile and chat persistence."""
import json
from pathlib import Path
from typing import Any

PROFILE_FIELDS = ("education_or_role", "location", "experience_level", "target_roles", "main_skills", "important_projects", "english_level", "preferred_work_mode", "weekly_hours", "career_goal")

def empty_profile() -> dict[str, str]: return {field: "" for field in PROFILE_FIELDS}
def load_saved_data(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict): raise ValueError
        return {"profile": {**empty_profile(), **(raw.get("profile") or {})}, "history": raw.get("history") if isinstance(raw.get("history"), list) else []}
    except (OSError, ValueError, json.JSONDecodeError):
        return {"profile": empty_profile(), "history": []}
def save_data(path: Path, profile: dict[str, str], history: list[dict[str, str]], enabled: bool) -> None:
    if not enabled: return
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_profile = {key: str(profile.get(key, "")) for key in PROFILE_FIELDS}
    path.write_text(json.dumps({"profile": safe_profile, "history": history[-100:]}, ensure_ascii=False, indent=2), encoding="utf-8")
def delete_saved_data(path: Path) -> None:
    try: path.unlink(missing_ok=True)
    except OSError as exc: raise RuntimeError(f"Could not delete saved personal data: {exc}") from exc
