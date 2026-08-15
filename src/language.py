import re

ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
LATIN_RE = re.compile(r"[A-Za-z]")

def detect_language(text: str) -> str:
    """Return ar, en, or mixed based on meaningful script characters."""
    ar, en = bool(ARABIC_RE.search(text)), bool(LATIN_RE.search(text))
    if ar and en: return "mixed"
    return "ar" if ar else "en"

def text_direction(text: str) -> str:
    return "rtl" if detect_language(text) == "ar" else "ltr"
