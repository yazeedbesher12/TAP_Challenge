from src.config import KB_PATH
from src.data_loader import load_knowledge_base
from src.fast_matcher import FastMatcher, instant_answer
from app import format_message_content

def test_common_career_queries_match_expected_intents():
    matcher = FastMatcher(load_knowledge_base(KB_PATH))
    checks = [
        ("من وين أبلش أدور على شغل؟", "start_career_guidance"),
        ("How can I improve my LinkedIn headline?", "write_linkedin_headline"),
        ("عندي remote interview ل junior data role", "start_mock_interview"),
        ("هل الشركات برا بتوظف من فلسطين؟", "remote_hiring_from_palestine"),
        ("هل الأربعة أشهر مع TAP مضمونة؟", "tap_job_timeline"),
        ("شو أكتب في CV إذا ما عندي خبرة رسمية؟", "cv_without_formal_experience"),
    ]
    for query, intent in checks:
        assert matcher.search(query)[0]["item"]["intent"] == intent

def test_instant_answer_uses_arabic_core_and_actions():
    matcher = FastMatcher(load_knowledge_base(KB_PATH))
    result = matcher.search("شو أكتب في CV إذا ما عندي خبرة رسمية؟")[0]
    answer = instant_answer(result, "ar", {"target_roles": "Junior AI Engineer"})
    assert result["item"]["answer_core_ar"] in answer
    assert "خطوات عملية:" in answer and "Junior AI Engineer" in answer

def test_skill_question_prefers_skill_gap_guidance_over_interview_prep():
    matcher = FastMatcher(load_knowledge_base(KB_PATH))
    result = matcher.search("What skills are needed for an AI Engineer?")[0]
    assert result["item"]["intent"] == "identify_skill_gap"
    answer = instant_answer(result, "en", {}, "What skills are needed for an AI Engineer?")
    assert "Python, SQL" in answer and "baseline model" in answer

def test_message_formatter_uses_compact_numbered_list_and_escapes_html():
    rendered = format_message_content("Practical steps:\n\n1. First <script>\n2. Second")
    assert "<ol>" in rendered and "&lt;<bdi dir=\"ltr\">script</bdi>&gt;" in rendered
