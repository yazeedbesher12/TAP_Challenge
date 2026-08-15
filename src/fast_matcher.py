"""Instant lexical matching for the small local TAP knowledge base.

For 47 records, loading an embedding model is unnecessary overhead. This matcher
runs in memory and returns known answers without starting Ollama.
"""
from __future__ import annotations
import re
from typing import Any

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u0600-\u06FF]+")
STOP_WORDS = {"كيف", "شو", "ما", "في", "من", "على", "عن", "the", "a", "an", "i", "my", "to", "for", "can", "is"}

def tokens(text: str) -> set[str]:
    cleaned = (word.lower().strip(".,!?؛،؟") for word in TOKEN_RE.findall(text))
    return {word for word in cleaned if len(word) > 1 and word not in STOP_WORDS}

class FastMatcher:
    def __init__(self, kb: dict[str, Any]):
        self.items = kb["items"]
        self.variant_tokens = [(item, tokens(variant)) for item in self.items for variant in item["question_variants"]]

    def search(self, query: str, top_k: int = 3, threshold: float = 0.20) -> list[dict[str, Any]]:
        query_tokens = tokens(query)
        if not query_tokens:
            return []
        best: dict[str, tuple[dict[str, Any], float]] = {}
        for item, variant in self.variant_tokens:
            overlap = len(query_tokens & variant)
            score = overlap / max(1, len(query_tokens | variant))
            # Exact domain terms are strong, cheap signals for the small KB.
            tag_tokens = tokens(" ".join(item.get("tags", [])))
            score += 0.15 * len(query_tokens & tag_tokens)
            current = best.get(item["id"])
            if current is None or score > current[1]:
                best[item["id"]] = (item, score)
        ranked = sorted(best.values(), key=lambda row: row[1], reverse=True)
        return [{"item": item, "score": score} for item, score in ranked[:top_k] if score >= threshold]

def instant_answer(match: dict[str, Any], language: str, profile: dict[str, str]) -> str:
    """Build a concise deterministic reply without invoking a language model."""
    item = match["item"]
    is_arabic = language in {"ar", "mixed"}
    core = item["answer_core_ar"] if is_arabic else item["answer_core_en"]
    steps = item.get("action_steps_ar" if is_arabic else "action_steps_en", [])
    heading = "خطوات عملية:" if is_arabic else "Practical steps:"
    answer = core
    if steps:
        answer += "\n\n" + heading + "\n" + "\n".join(f"{index}. {step}" for index, step in enumerate(steps, 1))
    target = profile.get("target_roles", "")
    if target:
        answer += f"\n\n{'الخطوة التالية:' if is_arabic else 'Next step:'} طبّق أول خطوة على هدفك: {target}."
    return answer
