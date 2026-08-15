from typing import Any

SETUP_KEYS = ("target_role", "requirements", "stage", "language")
def new_interview() -> dict[str, Any]: return {"active": True, "setup": {}, "question_number": 0, "answers": []}
def setup_complete(state: dict[str, Any]) -> bool: return all(state["setup"].get(k) for k in SETUP_KEYS)
def setup_prompt(state: dict[str, Any]) -> str:
    missing = [k for k in SETUP_KEYS if not state["setup"].get(k)]
    return "To start, share: " + ", ".join(missing) + "."
