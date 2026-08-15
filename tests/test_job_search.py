from pathlib import Path
from src.config import DEMO_PROFILE_PATH, JOBS_PATH
from src.data_loader import load_demo_profile
from src.job_search import JobSearchIndex, LocalJobProvider, is_job_search_intent, is_underspecified_job_request
from app import job_card_html, match_label
from streamlit.testing.v1 import AppTest

def index() -> JobSearchIndex:
    return JobSearchIndex(LocalJobProvider(JOBS_PATH).load())

def test_catalogue_is_valid_demo_data():
    jobs = LocalJobProvider(JOBS_PATH).load()
    assert len(jobs) == 20
    assert len({job["id"] for job in jobs}) == 20
    assert all(job["is_demo"] for job in jobs)
    assert all(job["apply_url"].startswith("https://") and ".example" in job["apply_url"] for job in jobs)

def test_job_intent_does_not_trigger_for_general_guidance():
    assert is_job_search_intent("بدي وظيفة AI Engineer")
    assert is_job_search_intent("Find a junior backend role in Amman")
    assert is_job_search_intent("Find a Junior Flutter Developer Remote in Jordan")
    assert is_job_search_intent("Show me a Python developer job that matches my skills")
    assert is_job_search_intent("اعرضلي وظيفة Backend Developer بتطلب Docker")
    assert is_job_search_intent("بدي Junior Flutter Developer Remote في الأردن")
    assert not is_job_search_intent("شو المهارات المطلوبة لوظيفة AI Engineer؟")
    assert not is_job_search_intent("بدي شغل")
    assert is_underspecified_job_request("بدي شغل")
    assert not is_underspecified_job_request("كيف أبدأ البحث عن عمل؟")

def test_bilingual_searches_rank_relevant_jobs_first():
    checks = [
        ("بدي وظيفة ذكاء اصطناعي في فلسطين", "JOB-001"),
        ("Find a junior backend role in Amman", "JOB-002"),
        ("دورلي على شغل UI UX", "JOB-004"),
        ("شو في وظيفة Flutter؟", "JOB-008"),
    ]
    for query, job_id in checks:
        assert index().search(query)[0]["job"]["id"] == job_id

def test_match_levels_cover_perfect_good_related_and_weak_search():
    assert index().search("Find a Junior Flutter Developer Remote in Jordan")[0]["match_level"] == "perfect"
    assert index().search("بدي Junior Flutter Developer Remote في الأردن")[0]["match_level"] == "perfect"
    assert index().search("Find a junior backend role in Amman")[0]["match_level"] == "good"
    assert index().search("Find a remote developer role")[0]["match_level"] == "related"
    assert index().search("Find a blockchain job") == []

def test_card_hides_demo_and_source_but_shows_translated_match_label():
    profile = load_demo_profile(DEMO_PROFILE_PATH)
    result = index().search("Find a Junior AI Engineer in Palestine", profile)[0]
    english = job_card_html(result, "en")
    arabic = job_card_html(result, "ar")
    assert "Demo Opportunity" not in english and "Source:" not in english
    assert result["job"]["source"] not in english and "is_demo" not in english
    assert "⭐ Suitable with a small gap" in english
    assert "⭐ مناسبة مع فجوة بسيطة" in arabic

def test_match_level_survives_structured_history_round_trip():
    result = index().search("Find a Junior AI Engineer in Palestine", load_demo_profile(DEMO_PROFILE_PATH))[0]
    history_event = {"role": "assistant", "jobs": [result], "job_language": "en"}
    assert history_event["jobs"][0]["match_level"] == "perfect"
    assert history_event["jobs"][0]["match_label_key"] == "suitable_small_gap"
    assert "⭐ Suitable with a small gap" in job_card_html(history_event["jobs"][0], history_event["job_language"])

def test_job_search_has_no_model_or_network_dependencies():
    source = Path("src/job_search.py").read_text(encoding="utf-8").lower()
    assert "ollama" not in source and "embedding" not in source
    assert "requests" not in source and "urllib" not in source

def test_quick_action_button_remains_removed():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run(timeout=20)
    assert not app.exception
    assert all("Find Jobs" not in button.label for button in app.button)

def test_broad_job_request_asks_for_clarification_without_cards():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run(timeout=20)
    app.chat_input[0].set_value("بدي شغل").run(timeout=20)
    rendered = "\n".join(markdown.value for markdown in app.markdown)
    assert not app.exception
    assert "الدور المستهدف" in rendered and "مستوى خبرتك" in rendered
    assert not app.expander and not app.radio

def test_inactive_or_expired_jobs_are_not_returned(tmp_path: Path):
    jobs = LocalJobProvider(JOBS_PATH).load()
    jobs[0] = {**jobs[0], "status": "inactive"}
    path = tmp_path / "jobs.json"; path.write_text(__import__("json").dumps(jobs), encoding="utf-8")
    results = JobSearchIndex(LocalJobProvider(path).load()).search("Find an AI Engineer job")
    assert all(result["job"]["id"] != "JOB-001" for result in results)
    jobs[0] = {**jobs[0], "status": "active", "expires_at": "2020-01-01"}
    path.write_text(__import__("json").dumps(jobs), encoding="utf-8")
    results = JobSearchIndex(LocalJobProvider(path).load()).search("Find an AI Engineer job")
    assert all(result["job"]["id"] != "JOB-001" for result in results)

def test_corrupt_catalogue_raises_clear_error(tmp_path: Path):
    path = tmp_path / "bad.json"; path.write_text("not json", encoding="utf-8")
    try:
        LocalJobProvider(path).load()
    except ValueError as exc:
        assert "Could not read" in str(exc)
    else:
        raise AssertionError("Malformed JSON should be rejected")
