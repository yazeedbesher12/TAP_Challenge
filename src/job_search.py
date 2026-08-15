"""Fast, deterministic search over the local demo job catalogue."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {"id", "title", "title_ar", "aliases", "company", "location", "work_mode", "employment_type", "experience_level", "skills", "description_en", "description_ar", "source", "apply_url", "is_demo", "status", "expires_at"}
TOKEN_RE = re.compile(r"[a-z0-9+#./-]+|[\u0621-\u064A]+", re.IGNORECASE)
SEARCH_PHRASES = (
    "بدي وظيفة", "دورلي", "ابحثلي", "لاقيلـي", "لاقيلي", "اعرضلي وظيفة", "اعرض لي وظيفة", "شغل مناسب", "فرص عمل", "شو في وظائف", "في فرص",
    "find me a job", "find a job", "find jobs", "show me a job", "show me a", "search for jobs", "job openings", "looking for a role", "hiring opportunities",
)
SEARCH_VERBS = {"بدي", "دورلي", "ابحثلي", "لاقيلي", "اعرضلي", "اعرض", "find", "show", "search", "looking", "need"}
ROLE_TERMS = {"developer", "engineer", "designer", "analyst", "backend", "frontend", "flutter", "mobile", "data", "ai", "ux", "ui", "remote"}
ALIASES = {
    "ذكاء اصطناعي": "ai", "تعلم آلي": "machine learning", "تحليل بيانات": "data analyst",
    "باك اند": "backend", "باك إند": "backend", "مبرمج خلفي": "backend", "مطور خلفي": "backend",
    "فرونت اند": "frontend", "واجهة امامية": "frontend", "فل ستاك": "full stack",
    "تجربة المستخدم": "ux", "امن سيبراني": "cybersecurity", "عن بعد": "remote",
    "مبتدئ": "junior", "متوسط الخبرة": "mid level",
    "الاردن": "jordan", "عمان": "amman", "فلسطين": "palestine",
}

def normalize(text: str) -> str:
    text = text.lower().replace("ـ", "").replace("_", " ")
    text = re.sub(r"[ً-ْ]", "", text)
    text = text.translate(str.maketrans({"أ":"ا", "إ":"ا", "آ":"ا", "ى":"ي", "ة":"ه"}))
    for source, replacement in ALIASES.items():
        text = text.replace(source, f" {replacement} ")
    return " ".join(TOKEN_RE.findall(text))

def token_set(text: str) -> set[str]:
    return set(normalize(text).split())

SKILL_ALIASES = {
    "js": "javascript",
    "react.js": "react",
    "reactjs": "react",
    "react js": "react",
    "nodejs": "node.js",
    "node.js": "node.js",
    "node js": "node.js",
    "rest api": "rest apis",
    "restful api": "rest apis",
    "rest apis": "rest apis",
    "fast api": "fastapi",
    "postgres": "postgresql",
    "ml": "machine learning",
    "docker containers": "docker",
}

def normalize_skill(skill: str) -> str:
    """Normalize harmless spelling variants without merging different tools."""
    value = re.sub(r"\s+", " ", str(skill).strip().lower())
    value = re.sub(r"[,;:_-]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return SKILL_ALIASES.get(value, value)

def normalize_skill_set(skills: list[str] | tuple[str, ...] | set[str]) -> set[str]:
    return {normalized for skill in skills if (normalized := normalize_skill(skill))}

def _job_skill_lists(job: dict[str, Any]) -> tuple[list[str], list[str]]:
    required = job.get("required_skills", job.get("skills", []))
    nice = job.get("nice_to_have_skills", [])
    return (required if isinstance(required, list) else [], nice if isinstance(nice, list) else [])

def analyze_skill_gap(user_skills: list[str], job: dict[str, Any]) -> dict[str, Any]:
    """Compare candidate skills with this job's actual required/optional fields."""
    user = normalize_skill_set(user_skills)
    required, nice = _job_skill_lists(job)
    matched_required = [skill for skill in required if normalize_skill(skill) in user]
    missing_required = [skill for skill in required if normalize_skill(skill) not in user]
    matched_nice = [skill for skill in nice if normalize_skill(skill) in user]
    missing_nice = [skill for skill in nice if normalize_skill(skill) not in user]
    ratio = len(matched_required) / len(required) if required else 1.0
    return {
        "matched_required_skills": matched_required,
        "missing_required_skills": missing_required,
        "matched_nice_to_have_skills": matched_nice,
        "missing_nice_to_have_skills": missing_nice,
        "required_match_ratio": ratio,
    }

def _role_families(text: str) -> set[str]:
    value = normalize(text)
    families: set[str] = set()
    mapping = {
        "backend": ("backend", "back end", "api developer"),
        "frontend": ("frontend", "front end", "react"),
        "fullstack": ("full stack", "full-stack"),
        "ai": (" ai ", "machine learning", " ml "),
        "data": ("data analyst", "data engineer", "data science"),
        "mobile": ("flutter", "mobile", "dart"),
        "design": ("ui ux", "designer", "graphic design"),
        "devops": ("devops", "cloud engineer"),
        "security": ("cybersecurity", "security analyst"),
    }
    padded = f" {value} "
    for family, markers in mapping.items():
        if any(marker in padded for marker in markers): families.add(family)
    return families

def _families_are_related(left: set[str], right: set[str]) -> bool:
    """Return whether two role-family sets are equivalent or intentionally adjacent."""
    if left & right:
        return True
    related_pairs = {("backend", "fullstack"), ("frontend", "fullstack"), ("ai", "data")}
    return any(
        (left_family, right_family) in related_pairs or (right_family, left_family) in related_pairs
        for left_family in left
        for right_family in right
    )

def role_compatibility(job: dict[str, Any], profile: dict[str, Any]) -> str:
    career = profile.get("career_profile", {}) if profile else {}
    job_roles = " ".join([str(job.get("title", "")), str(job.get("title_ar", "")), *[str(alias) for alias in job.get("aliases", [])]])
    target_families = _role_families(str(career.get("target_role", "")))
    other_families = _role_families(f"{career.get('bridge_role', '')} {career.get('dream_role', '')}")
    job_families = _role_families(job_roles)
    if target_families & job_families: return "target"
    if other_families & job_families: return "related"
    if _families_are_related(target_families, job_families):
        return "related"
    return "unrelated"

def _entry_level_incompatible(job: dict[str, Any], profile: dict[str, Any]) -> bool:
    level = normalize(str(profile.get("career_profile", {}).get("experience_level", ""))) if profile else ""
    job_level = normalize(str(job.get("experience_level", "")))
    return level in {"entry level", "junior"} and job_level in {"mid level", "mid-level", "senior"}

def classify_match(job: dict[str, Any], profile: dict[str, Any], gap_analysis: dict[str, Any], role_relation: str | None = None) -> str:
    """Classify fit after hard eligibility filters; optional skills never reject."""
    if job.get("status", "active") != "active" or _entry_level_incompatible(job, profile):
        return "exclude"
    relation = role_relation or role_compatibility(job, profile)
    missing = gap_analysis["missing_required_skills"]
    matched = gap_analysis["matched_required_skills"]
    ratio = gap_analysis["required_match_ratio"]
    if not missing and relation != "unrelated":
        return "highly_suitable"
    if len(missing) == 1 and ratio >= 0.70 and relation != "unrelated":
        return "suitable_small_gap"
    if relation != "unrelated" and (len(matched) >= 2 or ratio >= 0.40):
        return "related_opportunity"
    return "exclude"

def is_job_search_intent(message: str) -> bool:
    value = normalize(message)
    if any(normalize(phrase) in value for phrase in SEARCH_PHRASES):
        return True
    tokens = token_set(message)
    if tokens & SEARCH_VERBS and tokens & ROLE_TERMS:
        return True
    return bool(re.search(r"\b(find|looking for|i need)\b.*\b(job|role|position|developer|engineer|designer|analyst)\b", value))

def is_underspecified_job_request(message: str) -> bool:
    """Detect a tiny set of broad job phrases that need a role clarification."""
    broad_phrases = ("بدي شغل", "بدي عمل", "بدور على شغل", "I need work")
    return normalize(message) in {normalize(value) for value in broad_phrases}

@dataclass(frozen=True)
class IndexedJob:
    job: dict[str, Any]
    title: str
    aliases: str
    skills: str
    location: str
    work_mode: str
    experience: str
    all_terms: set[str]
    role_phrases: tuple[str, ...]

class LocalJobProvider:
    """Data provider separate from matching logic for a future live provider swap."""
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            raise FileNotFoundError(f"Job catalogue is missing: {self.path}")
        try:
            jobs = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not read local job catalogue: {exc}") from exc
        if not isinstance(jobs, list) or len(jobs) != 20:
            raise ValueError("Job catalogue must contain exactly 20 demo jobs.")
        ids: set[str] = set()
        for index, job in enumerate(jobs):
            missing = REQUIRED_FIELDS - set(job) if isinstance(job, dict) else REQUIRED_FIELDS
            if missing: raise ValueError(f"Job {index} has missing fields: {', '.join(sorted(missing))}")
            if job["id"] in ids: raise ValueError(f"Duplicate job id: {job['id']}")
            ids.add(job["id"])
            if not isinstance(job["aliases"], list) or not isinstance(job["skills"], list): raise ValueError(f"Job {job['id']} aliases and skills must be lists.")
            if not job["is_demo"]: raise ValueError(f"Job {job['id']} must be marked is_demo=true.")
            url = str(job["apply_url"])
            if not (url.startswith("https://") and url.split("/")[2].endswith(".example")): raise ValueError(f"Job {job['id']} has invalid demo apply_url.")
        return jobs

class JobSearchIndex:
    def __init__(self, jobs: list[dict[str, Any]]):
        self.index = [self._index(job) for job in jobs]
        self.catalogue_terms = set().union(*(item.all_terms for item in self.index))

    @staticmethod
    def _index(job: dict[str, Any]) -> IndexedJob:
        title = normalize(f"{job['title']} {job['title_ar']}")
        aliases = normalize(" ".join(job["aliases"]))
        skills = normalize(" ".join(job["skills"]))
        location = normalize(f"{job['location']} {job.get('country_code', '')}")
        work_mode, experience = normalize(job["work_mode"]), normalize(job["experience_level"])
        role_phrases = tuple(normalize(value) for value in (job["title"], job["title_ar"], *job["aliases"]) if normalize(value))
        return IndexedJob(job, title, aliases, skills, location, work_mode, experience, token_set(" ".join((title, aliases, skills, location, work_mode, experience))), role_phrases)

    @staticmethod
    def _profile_tokens(profile: dict[str, Any]) -> dict[str, set[str]]:
        career = profile.get("career_profile", {}) if profile else {}
        personal = profile.get("personal_information", {}) if profile else {}
        preferences = profile.get("work_preferences", {}) if profile else {}
        return {
            "target_role": token_set(str(career.get("target_role", ""))),
            "other_roles": token_set(" ".join(str(career.get(key, "")) for key in ("bridge_role", "dream_role"))),
            "skills": token_set(" ".join(str(skill) for skill in profile.get("skills", []))) if profile else set(),
            "location": token_set(f"{personal.get('city', '')} {personal.get('country', '')}"),
            "modes": token_set(" ".join(str(mode) for mode in preferences.get("preferred_modes", []))),
            "regions": token_set(" ".join(str(region) for region in preferences.get("preferred_regions", []))),
            "contracts": token_set(" ".join(str(kind) for kind in preferences.get("contract_types", []))),
            "level": normalize(str(career.get("experience_level", ""))),
        }

    def _requested_filters(self, query_tokens: set[str]) -> dict[str, set[str]]:
        locations = set().union(*(token_set(item.job["location"]) for item in self.index)) - {"remote", "mena"}
        modes = {"remote", "hybrid", "on-site", "onsite"}
        levels = {"junior", "mid", "senior"}
        return {
            "location": query_tokens & locations,
            "work_mode": query_tokens & modes,
            "experience": query_tokens & levels,
        }

    @staticmethod
    def _classify_match(item: IndexedJob, query_normalized: str, query_tokens: set[str], filters: dict[str, set[str]]) -> str:
        direct_role = any(phrase in query_normalized for phrase in item.role_phrases if len(token_set(phrase)) >= 2)
        role_overlap = len(query_tokens & token_set(item.title + " " + item.aliases))
        skill_overlap = len(query_tokens & token_set(item.skills))
        strong_role = direct_role or role_overlap >= 2 or (role_overlap >= 1 and skill_overlap >= 1)
        matches = {
            "location": not filters["location"] or bool(filters["location"] & token_set(item.location)),
            "work_mode": not filters["work_mode"] or bool(filters["work_mode"] & token_set(item.work_mode)),
            "experience": not filters["experience"] or bool(filters["experience"] & token_set(item.experience)),
        }
        requested_count = sum(bool(values) for values in filters.values())
        matched_count = sum(matches.values())
        core_conflict = bool(filters["work_mode"]) and not matches["work_mode"]
        if direct_role and matched_count == 3 and not core_conflict:
            return "perfect"
        if strong_role and not core_conflict and (requested_count == 0 or matched_count >= 2):
            return "good"
        return "related"

    def search(self, query: str, profile: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        query_normalized, query_tokens = normalize(query), token_set(query)
        query_role_families = _role_families(query)
        generic_search_tokens = {"find", "search", "looking", "need", "job", "jobs", "role", "position", "a", "an", "the", "i", "وظيفه", "وظائف", "بدي", "دورلي", "ابحثلي", "لاقيلي"}
        informative_query_terms = query_tokens - generic_search_tokens
        # Profile preferences may rank a broad request such as "Find a job", but
        # they must never invent a match for an unsupported specific field.
        if informative_query_terms and not (informative_query_terms & self.catalogue_terms):
            return []
        profile, filters = profile or {}, self._requested_filters(query_tokens)
        candidate = self._profile_tokens(profile)
        results: list[dict[str, Any]] = []
        for item in self.index:
            job, score = item.job, 0.0
            job_role_families = _role_families(" ".join((item.title, item.aliases)))
            # An explicit role family narrows the candidate set while intentionally
            # adjacent families (such as backend/full-stack or AI/data) may remain.
            if query_role_families and not _families_are_related(query_role_families, job_role_families):
                continue
            # Exact role phrases receive the strongest weight.
            for phrase in (item.title, item.aliases):
                if phrase and phrase in query_normalized: score += 40
            score += 10 * len(query_tokens & token_set(item.title))
            score += 6 * len(query_tokens & token_set(item.aliases))
            score += 2 * len(query_tokens & token_set(item.skills))
            score += 5 * len(query_tokens & token_set(item.location))
            score += 5 if item.work_mode in query_tokens else 0
            score += 3 if item.experience in query_normalized else 0
            # Only professional profile fields influence ranking; personal identity fields are ignored.
            score += 10 * len(candidate["target_role"] & token_set(item.title + " " + item.aliases))
            score += 3 * len(candidate["other_roles"] & token_set(item.title + " " + item.aliases))
            score += 2.5 * len(candidate["skills"] & token_set(item.skills))
            score += 3 * len(candidate["location"] & token_set(item.location))
            score += 3 if candidate["modes"] & token_set(item.work_mode) else 0
            score += 2 if candidate["regions"] & token_set(item.location + " MENA") else 0
            score += 2 if candidate["contracts"] & token_set(item.job["employment_type"]) else 0
            if job["status"] != "active" or date.fromisoformat(job["expires_at"]) < date.today():
                continue
            if _entry_level_incompatible(job, profile):
                continue
            if filters["location"] and not (filters["location"] & token_set(item.location)):
                continue
            if filters["work_mode"] and not (filters["work_mode"] & token_set(item.work_mode)):
                continue
            if filters["experience"] and not (filters["experience"] & token_set(item.experience)):
                continue
            if score >= 8:
                gap = analyze_skill_gap(profile.get("skills", []), job)
                relation = role_compatibility(job, profile)
                direct_query_role = any(phrase in query_normalized for phrase in item.role_phrases if len(token_set(phrase)) >= 2)
                if direct_query_role and relation == "unrelated": relation = "related"
                match_key = classify_match(job, profile, gap, relation) if profile else "related_opportunity"
                if match_key == "exclude":
                    continue
                legacy_level = self._classify_match(item, query_normalized, query_tokens, filters)
                label_priority = {"highly_suitable": 3, "suitable_small_gap": 2, "related_opportunity": 1}[match_key]
                relation_priority = {"target": 2, "related": 1, "unrelated": 0}[relation]
                preference_score = (
                    int(bool(candidate["location"] & token_set(item.location)))
                    + int(bool(candidate["modes"] & token_set(item.work_mode)))
                    + int(bool(candidate["contracts"] & token_set(job["employment_type"])))
                )
                results.append({
                    "job": job,
                    "score": score,
                    "match_level": legacy_level,
                    "match_label_key": match_key,
                    "next_action_key": match_key,
                    **gap,
                    "missing_skills": gap["missing_required_skills"],
                    # Kept structured for deterministic ranking/history; never displayed as raw debug data.
                    "role_compatibility": relation,
                    "_rank": (label_priority, gap["required_match_ratio"], relation_priority, preference_score, score),
                })
        ordered = sorted(
            results,
            key=lambda result: tuple(-value for value in result["_rank"]) + (result["job"]["id"],),
        )[:min(top_k, 3)]
        for result in ordered:
            result.pop("_rank", None)
        return ordered
