"""Instant lexical matching for the small local TAP knowledge base.

For 47 records, loading an embedding model is unnecessary overhead. This matcher
runs in memory and returns known answers without starting Ollama.
"""
from __future__ import annotations
import re
from typing import Any

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u0600-\u06FF]+")
STOP_WORDS = {"كيف", "شو", "ما", "في", "من", "على", "عن", "the", "a", "an", "i", "my", "to", "for", "can", "is"}
TEXT_ALIASES = (
    (re.compile(r"(?:السيرة|سيرة)\s+الذاتية|سيرة\s+ذاتية|سي\s*في|resume", re.IGNORECASE), " cv "),
    (re.compile(r"ذكاء\s+اصطناعي", re.IGNORECASE), " ai "),
    (re.compile(r"تعلم\s+(?:الالة|الاله|آلي)", re.IGNORECASE), " machine learning "),
)

def normalize_text(text: str) -> str:
    value = text.lower().replace("ـ", "")
    value = re.sub(r"[\u064B-\u065F\u0670]", "", value)
    value = value.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    for pattern, replacement in TEXT_ALIASES:
        value = pattern.sub(replacement, value)
    return value

def tokens(text: str) -> set[str]:
    cleaned = (word.lower().strip(".,!?؛،؟") for word in TOKEN_RE.findall(normalize_text(text)))
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
            # A skill-gap question is guidance, not interview preparation. This
            # lightweight intent cue resolves otherwise-close AI wording.
            query_lower = normalize_text(query)
            skill_question = ("skills" in query_lower or "skill" in query_lower or "مهارات" in query_lower) and "interview" not in query_lower and "مقابلة" not in query_lower
            if skill_question and item.get("intent") == "identify_skill_gap":
                score += 0.30
            cv_question = "cv" in query_tokens
            if cv_question:
                intent = item.get("intent")
                no_experience = any(term in query_lower for term in ("بدون خبرة", "بدون خبره", "ما عندي خبرة", "ما عندي خبره", "no experience", "never worked"))
                if no_experience and intent == "cv_without_formal_experience":
                    score += 0.70
                elif not no_experience and intent == "cv_structure":
                    score += 0.55
            current = best.get(item["id"])
            if current is None or score > current[1]:
                best[item["id"]] = (item, score)
        ranked = sorted(best.values(), key=lambda row: row[1], reverse=True)
        return [{"item": item, "score": score} for item, score in ranked[:top_k] if score >= threshold]

def instant_answer(match: dict[str, Any], language: str, profile: dict[str, str], query: str = "") -> str:
    """Build a concise deterministic reply without invoking a language model."""
    item = match["item"]
    is_arabic = language in {"ar", "mixed"}
    core = item["answer_core_ar"] if is_arabic else item["answer_core_en"]
    steps = item.get("action_steps_ar" if is_arabic else "action_steps_en", [])
    query_lower = query.lower()
    ai_skill_question = item.get("intent") == "identify_skill_gap" and ("ai engineer" in query_lower or "ذكاء اصطناعي" in query_lower)
    if ai_skill_question:
        if is_arabic:
            core = "لدور AI Engineer ركّز أولًا على Python وSQL وتجهيز البيانات ومبادئ Machine Learning، ثم اثبتها بمشروع واضح بدل جمع شهادات كثيرة."
            steps = ["اختر مشروعًا صغيرًا: بيانات، نموذج baseline، ومقياس واضح للنتيجة.", "اكتب في README كيف نظّفت البيانات، اخترت النموذج، وقست الأخطاء.", "قارن متطلبات ثلاث وظائف Junior AI Engineer وحدد فجوتين فقط للتعلّم التالي."]
        else:
            core = "For an AI Engineer role, prioritize Python, SQL, data preparation, and core machine-learning concepts, then prove them through one clear project instead of collecting many certificates."
            steps = ["Build a small project with data preparation, a baseline model, and one measurable result.", "Document how you cleaned data, chose the model, and evaluated errors in the README.", "Compare three Junior AI Engineer postings and choose only two gaps for your next learning cycle."]
    heading = "خطوات عملية:" if is_arabic else "Practical steps:"
    answer = core
    if steps:
        answer += "\n\n" + heading + "\n" + "\n".join(f"{index}. {step}" for index, step in enumerate(steps, 1))
    target = profile.get("target_roles", "")
    if target:
        answer += f"\n\n{'الخطوة التالية:' if is_arabic else 'Next step:'} طبّق أول خطوة على هدفك: {target}."
    return answer
