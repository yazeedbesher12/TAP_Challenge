from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB_PATH = ROOT / "tap_career_companion_qa.json"
JOBS_PATH = ROOT / "data" / "jobs.json"
DEMO_PROFILE_PATH = ROOT / "data" / "demo_user_profile.json"
LEARNING_RESOURCES_PATH = ROOT / "data" / "learning_resources.json"
SKILL_ASSESSMENTS_PATH = ROOT / "data" / "skill_assessment_questions.json"
READINESS_RULES_PATH = ROOT / "data" / "readiness_rules.json"
MEMORY_PATH = ROOT / "data" / "personal_memory.json"
FAST_MATCH_THRESHOLD = 0.20
