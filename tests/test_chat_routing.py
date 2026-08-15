import html
import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.chat_routing import find_role_fragment, find_typed_assessment_option, is_roadmap_ui_request
from src.config import JOBS_PATH, KB_PATH, SKILL_ASSESSMENTS_PATH
from src.data_loader import load_knowledge_base, load_skill_assessments
from src.fast_matcher import FastMatcher, instant_answer
from src.job_search import LocalJobProvider


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def test_arabic_cv_question_routes_to_cv_structure():
    matcher = FastMatcher(load_knowledge_base(KB_PATH))
    result = matcher.search("كيف أكتب سيرة ذاتية قوية؟")[0]
    assert result["item"]["intent"] == "cv_structure"
    answer = instant_answer(result, "ar", {}, "كيف أكتب سيرة ذاتية قوية؟")
    assert "Skills" in answer and "Experience" in answer and "Projects" in answer


def test_ai_engineer_skills_answer_is_specific_not_generic():
    matcher = FastMatcher(load_knowledge_base(KB_PATH))
    result = matcher.search("What skills are needed for an AI Engineer?")[0]
    answer = instant_answer(result, "en", {}, "What skills are needed for an AI Engineer?")
    assert "Python" in answer and "SQL" in answer and "machine-learning" in answer
    assert "baseline model" in answer


def test_docker_options_typed_in_chat_are_recognized():
    catalog = load_skill_assessments(SKILL_ASSESSMENTS_PATH)
    first = find_typed_assessment_option("الimage قالب ثابت والcontainer نسخة تعمل منه", catalog)
    second = find_typed_assessment_option("تحديد خطوات بناء Docker image", catalog)
    assert first == {"skill": "Docker", "question_id": "docker_q2"}
    assert second == {"skill": "Docker", "question_id": "docker_q1"}


def test_roadmap_label_and_data_analyst_fragment_are_recognized():
    assert is_roadmap_ui_request("خطة قصيرة لسد فجوة المهارات")
    jobs = LocalJobProvider(JOBS_PATH).load()
    role = find_role_fragment("محلل بيانات محترف", jobs)
    assert role and role["id"] == "JOB-005"


def test_screenshot_queries_never_receive_the_generic_fallback():
    expected_phrases = {
        "الimage قالب ثابت والcontainer نسخة تعمل منه": "إجابة من اختبار Docker",
        "تحديد خطوات بناء Docker image": "إجابة من اختبار Docker",
        "خطة قصيرة لسد فجوة المهارات": "ابحث أولًا عن وظيفة محددة",
        "كيف أكتب سيرة ذاتية قوية؟": "Projects",
        "محلل بيانات محترف": "أقرب دور متوفر في بيانات الديمو",
        "What skills are needed for an AI Engineer?": "baseline model",
    }
    for query, expected in expected_phrases.items():
        app = AppTest.from_file(APP_PATH).run(timeout=20)
        app.chat_input[0].set_value(query).run(timeout=20)
        rendered = "\n".join(markdown.value for markdown in app.markdown)
        visible_text = html.unescape(re.sub(r"<[^>]+>", "", rendered))
        assert not app.exception
        assert expected in visible_text, query
        assert "لإجابة أدق، اكتب" not in visible_text, query
