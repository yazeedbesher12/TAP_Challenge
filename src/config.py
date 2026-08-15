from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB_PATH = ROOT / "tap_career_companion_qa.json"
MEMORY_PATH = ROOT / "data" / "personal_memory.json"
FAST_MATCH_THRESHOLD = 0.20
