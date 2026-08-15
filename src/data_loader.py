"""Knowledge-base loading and schema validation."""
import json
import math
from pathlib import Path
from typing import Any

REQUIRED = ("id", "category", "intent", "question_variants", "answer_core_ar", "answer_core_en")
DEMO_PROFILE_REQUIRED = ("profile_id", "profile_type", "personal_information", "career_profile", "skills", "work_preferences", "privacy")
LEARNING_RESOURCE_REQUIRED = (
    "skill", "aliases", "estimated_hours", "why_ar", "why_en", "resource",
    "roadmap", "evidence_ar", "evidence_en", "completion_criteria",
)

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

def load_demo_profile(path: Path) -> dict[str, Any]:
    """Load the single fictional demo profile without mutating it."""
    if not path.exists():
        raise FileNotFoundError(f"Demo profile is missing: {path}")
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read demo profile: {exc}") from exc
    validate_demo_profile(profile)
    return profile

def validate_demo_profile(profile: dict[str, Any]) -> None:
    if not isinstance(profile, dict):
        raise ValueError("Demo profile must be a JSON object.")
    missing = [field for field in DEMO_PROFILE_REQUIRED if field not in profile]
    if missing:
        raise ValueError(f"Demo profile is missing fields: {', '.join(missing)}")
    if not isinstance(profile["personal_information"], dict) or not isinstance(profile["career_profile"], dict):
        raise ValueError("Demo profile personal and career sections must be objects.")
    if not isinstance(profile["work_preferences"], dict) or not isinstance(profile["privacy"], dict):
        raise ValueError("Demo profile preferences and privacy sections must be objects.")
    if not isinstance(profile["skills"], list) or not all(isinstance(skill, str) and skill.strip() for skill in profile["skills"]):
        raise ValueError("Demo profile skills must be a non-empty list of strings.")

def load_learning_resources(path: Path) -> dict[str, Any]:
    """Load and validate the static bilingual learning catalogue read-only."""
    if not path.exists():
        raise FileNotFoundError(f"Learning-resources file is missing: {path}")
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read learning resources: {exc}") from exc
    validate_learning_resources(catalog)
    return catalog

def validate_learning_resources(catalog: dict[str, Any]) -> None:
    if not isinstance(catalog, dict):
        raise ValueError("Learning-resources catalogue must be a JSON object.")
    for field in ("catalog_version", "catalog_type", "rules", "resources", "fallback"):
        if field not in catalog:
            raise ValueError(f"Learning-resources catalogue is missing '{field}'.")
    resources = catalog["resources"]
    if not isinstance(resources, list) or not resources:
        raise ValueError("Learning-resources 'resources' must be a non-empty array.")
    rules = catalog["rules"]
    if not isinstance(rules, dict) or not isinstance(rules.get("max_roadmaps_per_job"), int):
        raise ValueError("Learning-resources rules must define max_roadmaps_per_job.")
    seen: set[str] = set()
    for index, resource in enumerate(resources):
        if not isinstance(resource, dict):
            raise ValueError(f"Learning resource {index} must be an object.")
        missing = [field for field in LEARNING_RESOURCE_REQUIRED if field not in resource]
        if missing:
            raise ValueError(f"Learning resource {index} is missing fields: {', '.join(missing)}.")
        skill = resource["skill"]
        if not isinstance(skill, str) or not skill.strip():
            raise ValueError(f"Learning resource {index} has an invalid skill.")
        normalized_skill = " ".join(skill.casefold().split())
        if normalized_skill in seen:
            raise ValueError(f"Duplicate learning resource skill: {skill}.")
        seen.add(normalized_skill)
        if not isinstance(resource["aliases"], list) or not all(isinstance(alias, str) and alias.strip() for alias in resource["aliases"]):
            raise ValueError(f"Learning resource '{skill}' has invalid aliases.")
        if not isinstance(resource["estimated_hours"], (int, float)) or resource["estimated_hours"] <= 0:
            raise ValueError(f"Learning resource '{skill}' has invalid estimated hours.")
        if not all(isinstance(resource[field], str) and resource[field].strip() for field in ("why_ar", "why_en", "evidence_ar", "evidence_en")):
            raise ValueError(f"Learning resource '{skill}' has invalid bilingual content.")
        link = resource["resource"]
        if not isinstance(link, dict) or not all(isinstance(link.get(field), str) and link[field].strip() for field in ("title", "provider", "url")):
            raise ValueError(f"Learning resource '{skill}' has invalid link metadata.")
        if not link["url"].startswith("https://"):
            raise ValueError(f"Learning resource '{skill}' URL must use HTTPS.")
        steps = resource["roadmap"]
        expected_stages = {"learn", "build", "evaluate", "portfolio"}
        if not isinstance(steps, list) or {step.get("stage") for step in steps if isinstance(step, dict)} != expected_stages:
            raise ValueError(f"Learning resource '{skill}' must contain the four roadmap stages.")
        if not all(
            isinstance(step.get("ar"), str) and step["ar"].strip()
            and isinstance(step.get("en"), str) and step["en"].strip()
            and isinstance(step.get("hours"), (int, float)) and step["hours"] >= 0
            for step in steps
        ):
            raise ValueError(f"Learning resource '{skill}' has invalid roadmap steps.")
        if not isinstance(resource["completion_criteria"], list) or not all(isinstance(value, str) and value.strip() for value in resource["completion_criteria"]):
            raise ValueError(f"Learning resource '{skill}' has invalid completion criteria.")
    fallback = catalog["fallback"]
    if not isinstance(fallback, dict):
        raise ValueError("Learning-resources fallback must be an object.")
    for field in ("estimated_hours", "ar", "en", "warning_ar", "warning_en"):
        if field not in fallback:
            raise ValueError(f"Learning-resources fallback is missing '{field}'.")
    if not isinstance(fallback["estimated_hours"], (int, float)) or fallback["estimated_hours"] <= 0:
        raise ValueError("Learning-resources fallback has invalid estimated hours.")
    if not all(
        isinstance(fallback.get(language), list)
        and len(fallback[language]) >= 4
        and all(isinstance(step, str) and step.strip() for step in fallback[language])
        for language in ("ar", "en")
    ):
        raise ValueError("Learning-resources fallback must contain four Arabic and English steps.")
    if not all(isinstance(fallback[field], str) and fallback[field].strip() for field in ("warning_ar", "warning_en")):
        raise ValueError("Learning-resources fallback warnings must be bilingual text.")

def load_skill_assessments(path: Path) -> dict[str, Any]:
    """Load and validate the static bilingual assessment catalogue read-only."""
    if not path.exists():
        raise FileNotFoundError(f"Skill-assessment file is missing: {path}")
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read skill assessments: {exc}") from exc
    validate_skill_assessments(catalog)
    return catalog

def validate_skill_assessments(catalog: dict[str, Any]) -> None:
    if not isinstance(catalog, dict):
        raise ValueError("Skill-assessment catalogue must be a JSON object.")
    for field in ("assessment_rules", "result_labels", "assessments", "fallback"):
        if field not in catalog:
            raise ValueError(f"Skill-assessment catalogue is missing '{field}'.")
    rules = catalog["assessment_rules"]
    if not isinstance(rules, dict):
        raise ValueError("Skill-assessment rules must be an object.")
    questions_per_skill = rules.get("questions_per_skill")
    passing_score = rules.get("passing_score_percentage")
    if questions_per_skill != 3:
        raise ValueError("Skill-assessment rules must define questions_per_skill as 3 for this demo.")
    if not isinstance(passing_score, (int, float)) or not 0 <= passing_score <= 100:
        raise ValueError("Skill-assessment rules must define a valid passing_score_percentage.")
    result_labels = catalog["result_labels"]
    if not isinstance(result_labels, dict) or not all(
        isinstance(result_labels.get(label), dict)
        and all(isinstance(result_labels[label].get(language), str) and result_labels[label][language].strip() for language in ("ar", "en"))
        for label in ("passed", "needs_practice")
    ):
        raise ValueError("Skill-assessment result labels must contain passed and needs_practice in both languages.")
    assessments = catalog["assessments"]
    if not isinstance(assessments, list):
        raise ValueError("Skill-assessment 'assessments' must be a list.")
    question_ids: set[str] = set()
    for assessment_index, assessment in enumerate(assessments):
        if not isinstance(assessment, dict):
            raise ValueError(f"Assessment {assessment_index} must be an object.")
        skill, questions = assessment.get("skill"), assessment.get("questions")
        if not isinstance(skill, str) or not skill.strip():
            raise ValueError(f"Assessment {assessment_index} has an invalid skill.")
        if not isinstance(questions, list) or len(questions) < questions_per_skill:
            raise ValueError(f"Assessment '{skill}' must contain at least {questions_per_skill} questions.")
        aliases = assessment.get("aliases", [])
        if not isinstance(aliases, list) or not all(isinstance(alias, str) and alias.strip() for alias in aliases):
            raise ValueError(f"Assessment '{skill}' has invalid aliases.")
        for question_index, question in enumerate(questions):
            if not isinstance(question, dict):
                raise ValueError(f"Question {question_index} in '{skill}' must be an object.")
            question_id = question.get("id")
            if not isinstance(question_id, str) or not question_id.strip():
                raise ValueError(f"Question {question_index} in '{skill}' has an invalid id.")
            if question_id in question_ids:
                raise ValueError(f"Duplicate assessment question id: {question_id}.")
            question_ids.add(question_id)
            for field in ("question_ar", "question_en", "explanation_ar", "explanation_en"):
                if not isinstance(question.get(field), str) or not question[field].strip():
                    raise ValueError(f"Question '{question_id}' is missing bilingual text or explanation.")
            options = question.get("options")
            if not isinstance(options, list) or len(options) < 2:
                raise ValueError(f"Question '{question_id}' must contain options.")
            option_ids: set[str] = set()
            for option in options:
                if not isinstance(option, dict) or not all(isinstance(option.get(field), str) and option[field].strip() for field in ("id", "ar", "en")):
                    raise ValueError(f"Question '{question_id}' has an invalid option.")
                if option["id"] in option_ids:
                    raise ValueError(f"Question '{question_id}' has duplicate option id '{option['id']}'.")
                option_ids.add(option["id"])
            if question.get("correct_option_id") not in option_ids:
                raise ValueError(f"Question '{question_id}' correct_option_id does not match an option.")
    fallback = catalog["fallback"]
    if not isinstance(fallback, dict) or not all(isinstance(fallback.get(language), str) and fallback[language].strip() for language in ("ar", "en")):
        raise ValueError("Skill-assessment fallback must contain Arabic and English text.")

def load_readiness_rules(path: Path) -> dict[str, Any]:
    """Load and validate the static readiness rules without modifying them."""
    if not path.exists():
        raise FileNotFoundError(f"Readiness-rules file is missing: {path}")
    try:
        rules = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read readiness rules: {exc}") from exc
    validate_readiness_rules(rules)
    return rules

def validate_readiness_rules(rules: dict[str, Any]) -> None:
    if not isinstance(rules, dict):
        raise ValueError("Readiness rules must be a JSON object.")
    for field in ("score", "statuses", "gates", "actions", "display", "empty_states", "disclaimer"):
        if field not in rules:
            raise ValueError(f"Readiness rules are missing '{field}'.")
    score = rules["score"]
    weights = score.get("weights") if isinstance(score, dict) else None
    if not isinstance(weights, dict) or set(weights) != {"job_match_score", "skill_assessment_score"}:
        raise ValueError("Readiness score weights must define job_match_score and skill_assessment_score.")
    if not all(isinstance(value, (int, float)) and value >= 0 for value in weights.values()) or not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-9):
        raise ValueError("Readiness score weights must be non-negative and sum to 1.0.")
    statuses = rules["statuses"]
    if not isinstance(statuses, list) or not statuses:
        raise ValueError("Readiness statuses must be a non-empty list.")
    status_ids: set[str] = set()
    coverage = [0] * 101
    for index, status in enumerate(statuses):
        if not isinstance(status, dict) or not isinstance(status.get("id"), str) or not status["id"].strip():
            raise ValueError(f"Readiness status {index} has an invalid id.")
        if status["id"] in status_ids:
            raise ValueError(f"Duplicate readiness status id: {status['id']}.")
        status_ids.add(status["id"])
        if not all(isinstance(status.get(field), str) and status[field].strip() for field in ("label_ar", "label_en", "primary_action")):
            raise ValueError(f"Readiness status '{status['id']}' is missing bilingual labels or a primary action.")
        minimum, maximum = status.get("minimum_score"), status.get("maximum_score")
        if minimum is None and maximum is None:
            continue
        if not isinstance(minimum, int) or not isinstance(maximum, int) or not 0 <= minimum <= maximum <= 100:
            raise ValueError(f"Readiness status '{status['id']}' has an invalid score range.")
        for value in range(minimum, maximum + 1):
            coverage[value] += 1
    if any(count != 1 for count in coverage):
        raise ValueError("Scored readiness statuses must cover every score from 0 to 100 exactly once.")
    actions = rules["actions"]
    if not isinstance(actions, dict):
        raise ValueError("Readiness actions must be an object.")
    for status in statuses:
        action_id = status["primary_action"]
        action = actions.get(action_id)
        if not isinstance(action, dict) or not all(isinstance(action.get(f"label_{language}"), str) and action[f"label_{language}"].strip() for language in ("ar", "en")):
            raise ValueError(f"Readiness status '{status['id']}' references an invalid primary action '{action_id}'.")
    gates = rules["gates"]
    if not isinstance(gates, list):
        raise ValueError("Readiness gates must be a list.")
    for gate in gates:
        if not isinstance(gate, dict):
            raise ValueError("Each readiness gate must be an object.")
        reference = gate.get("status") if gate.get("effect") == "set_status" else gate.get("maximum_status")
        if reference not in status_ids:
            raise ValueError(f"Readiness gate '{gate.get('id', '')}' references unknown status '{reference}'.")
        if gate.get("effect") == "cap_status" and not all(isinstance(gate.get(f"message_{language}"), str) and gate[f"message_{language}"].strip() for language in ("ar", "en")):
            raise ValueError(f"Readiness gate '{gate.get('id', '')}' is missing bilingual messages.")
    disclaimer = rules["disclaimer"]
    if not isinstance(disclaimer, dict) or not all(isinstance(disclaimer.get(language), str) and disclaimer[language].strip() for language in ("ar", "en")):
        raise ValueError("Readiness disclaimer must contain Arabic and English text.")
