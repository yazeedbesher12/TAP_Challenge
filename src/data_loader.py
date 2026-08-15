"""Knowledge-base loading and schema validation."""
import json
from pathlib import Path
from typing import Any

REQUIRED = ("id", "category", "intent", "question_variants", "answer_core_ar", "answer_core_en")

def load_knowledge_base(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Knowledge-base file is missing: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read knowledge base: {exc}") from exc
    validate_knowledge_base(data)
    return data

def validate_knowledge_base(data: dict[str, Any]) -> None:
    if not isinstance(data, dict): raise ValueError("Knowledge base must be a JSON object.")
    for key in ("metadata", "assistant_policy"):
        if key not in data: raise ValueError(f"Knowledge base is missing '{key}'.")
    items = data.get("items")
    if not isinstance(items, list) or not items: raise ValueError("Knowledge base 'items' must be a non-empty array.")
    ids: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict): raise ValueError(f"Item {index} must be an object.")
        missing = [field for field in REQUIRED if not item.get(field)]
        if missing: raise ValueError(f"Item {index} is missing or has empty required fields: {', '.join(missing)}.")
        if not isinstance(item["question_variants"], list) or not all(isinstance(x, str) and x.strip() for x in item["question_variants"]):
            raise ValueError(f"Item '{item['id']}' has invalid question_variants.")
        if item["id"] in ids: raise ValueError(f"Duplicate knowledge item id: {item['id']}.")
        ids.add(item["id"])
