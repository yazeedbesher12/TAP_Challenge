from __future__ import annotations
import html
import re
from typing import Any
import streamlit as st
from src.config import DEMO_PROFILE_PATH, FAST_MATCH_THRESHOLD, JOBS_PATH, KB_PATH, LEARNING_RESOURCES_PATH, MEMORY_PATH, READINESS_RULES_PATH, SKILL_ASSESSMENTS_PATH
from src.data_loader import load_demo_profile, load_knowledge_base, load_learning_resources, load_readiness_rules, load_skill_assessments
from src.language import detect_language, text_direction
from src.memory import delete_saved_data, empty_profile, load_saved_data, save_data
from src.fast_matcher import FastMatcher, instant_answer
from src.job_search import JobSearchIndex, LocalJobProvider, is_job_search_intent, is_underspecified_job_request
from src.learning_roadmap import build_skill_roadmaps
from src.skill_assessment import assessment_questions, calculate_assessment_result, select_assessment_skills
from src.readiness import calculate_readiness
from src.chat_routing import find_role_fragment, find_typed_assessment_option, is_roadmap_ui_request
from src.safety import boundary_response

st.set_page_config(page_title="TAP Career Companion", page_icon="💼", layout="centered")

def inject_styles() -> None:
    """Static visual styling; user content is never interpolated here."""
    st.markdown("""
    <style>
      .stApp { background: #f6f8fc; }
      .block-container { max-width: 920px; padding-top: 2rem; padding-bottom: 6rem; }
      [data-testid="stSidebar"] { background: linear-gradient(180deg, #112b46, #193d5e); }
      [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
      [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stCaption,
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #f4f8fc; }
      [data-testid="stSidebar"] input { color: #17263a !important; background: #ffffff !important; }
      [data-testid="stSidebar"] [data-baseweb="select"] input,
      [data-testid="stSidebar"] [data-baseweb="select"] div { color: #17263a !important; }
      .tap-hero { background: linear-gradient(120deg, #123b5b, #0e7490); border-radius: 20px; padding: 1.5rem 1.6rem; color: white; box-shadow: 0 12px 30px rgba(16,55,84,.18); margin-bottom: 1.25rem; }
      .tap-hero h1 { margin: 0; font-size: 2rem; color: white; }
      .tap-hero p { margin: .35rem 0 0; color: #d9f4f5; font-size: 1rem; }
      .tap-badge { display:inline-block; margin-top:.9rem; background:rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.3); padding:.28rem .7rem; border-radius:999px; font-size:.8rem; font-weight:600; }
      [data-testid="stChatMessage"] { background:#fff; border:1px solid #e5ebf2; border-radius:16px; padding:.35rem .55rem; box-shadow:0 3px 12px rgba(28,57,86,.05); }
      [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
      [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
      [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li,
      [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] span,
      [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] div { color:#162c42 !important; }
      .chat-message-text p { margin:0 0 .45rem; }
      .chat-message-text ol { margin:.35rem 0 0; padding-inline-start:1.45rem; }
      .chat-message-text li { margin:.3rem 0; }
      .job-card { background:#ffffff !important; border:1px solid #d9e4ee !important; border-radius:16px; padding:1.25rem; margin:1rem 0; box-shadow:0 4px 14px rgba(28,57,86,.07); }
      .job-card, .job-card * { color:#162c42 !important; }
      .job-card__title { margin:0 0 .35rem; font-size:1.35rem; font-weight:750; }
      .job-card__meta { margin:.25rem 0; color:#466176 !important; font-size:.9rem; }
      .job-card__skills { color:#0e7490 !important; font-weight:600; font-size:.9rem; }
      .job-card__description { line-height:1.6; margin:.85rem 0; }
      .job-card__match { display:inline-block; border-radius:999px; padding:.22rem .62rem; font-size:.8rem; font-weight:750; margin-bottom:.65rem; }
      .job-card__match--highly_suitable, .job-card__match--perfect { background:#dcfce7; color:#166534 !important; }
      .job-card__match--suitable_small_gap, .job-card__match--good { background:#e0e7ff; color:#3730a3 !important; }
      .job-card__match--related_opportunity, .job-card__match--related { background:#ffedd5; color:#9a3412 !important; }
      .job-card__gap { background:#f8fafc; border-radius:10px; padding:.65rem .75rem; margin:.55rem 0; }
      .job-card__gap strong { color:#29455c !important; }
      .job-card__next { border-inline-start:3px solid #0e7490; padding-inline-start:.7rem; margin-top:.8rem; font-weight:600; }
      .job-card__apply { display:block; background:#123b5b !important; color:#ffffff !important; text-align:center; text-decoration:none; font-weight:700; border-radius:9px; padding:.65rem 1rem; margin-top:1rem; }
      .job-card__apply:hover { background:#0e7490 !important; color:#ffffff !important; }
      .roadmap-card { border:1px solid #d9e4ee; border-radius:12px; padding:.85rem 1rem; margin:.65rem 0; background:#fbfdff; color:#162c42; }
      .roadmap-card h4 { margin:0 0 .5rem; color:#123b5b; }
      .roadmap-card p { margin:.35rem 0; line-height:1.5; }
      .roadmap-card ol { margin:.45rem 0; padding-inline-start:1.35rem; }
      .roadmap-card a { color:#0e7490 !important; font-weight:650; }
      .assessment-result { border:1px solid #d9e4ee; border-radius:12px; padding:.8rem 1rem; margin:.65rem 0; background:#fbfdff; color:#162c42; }
      .assessment-result--passed { border-inline-start:4px solid #16a34a; }
      .assessment-result--practice { border-inline-start:4px solid #ea580c; }
      .assessment-result a { color:#0e7490 !important; font-weight:650; }
      .readiness-card { border:1px solid #cbdbe8; border-radius:14px; padding:1rem; background:#f8fbfd; color:#162c42; }
      .readiness-card h4 { margin:0 0 .5rem; }
      .readiness-card ul { margin:.35rem 0; padding-inline-start:1.3rem; }
      .readiness-card a { color:#0e7490 !important; font-weight:700; }
      .readiness-card__formula { color:#466176; font-size:.9rem; }
      .readiness-card__gate { background:#fff7ed; border-radius:8px; padding:.5rem .65rem; }
      [data-testid="stChatInput"] { border-radius:16px; border:1px solid #b9c9d8; box-shadow:0 7px 22px rgba(28,57,86,.10); }
      .stButton > button { border-radius:10px; border:1px solid #7aa8be; font-weight:600; }
      @media (max-width:640px) { .block-container { padding:1rem .8rem 5rem; } .tap-hero { padding:1.2rem; border-radius:16px; } .tap-hero h1 { font-size:1.55rem; } }
    </style>
    """, unsafe_allow_html=True)
@st.cache_resource
def services() -> tuple[dict[str, Any], FastMatcher]:
    kb = load_knowledge_base(KB_PATH)
    return kb, FastMatcher(kb)

@st.cache_resource(show_spinner=False)
def job_index(file_mtime_ns: int) -> JobSearchIndex:
    """Load and index the local catalogue once per file version."""
    del file_mtime_ns
    return JobSearchIndex(LocalJobProvider(JOBS_PATH).load())

@st.cache_resource(show_spinner=False)
def demo_profile(file_mtime_ns: int) -> dict[str, Any]:
    """Cache the immutable fictional profile by its file version."""
    del file_mtime_ns
    return load_demo_profile(DEMO_PROFILE_PATH)

@st.cache_resource(show_spinner=False)
def learning_catalog(file_mtime_ns: int) -> dict[str, Any]:
    """Load the validated static roadmap catalogue once per file version."""
    del file_mtime_ns
    return load_learning_resources(LEARNING_RESOURCES_PATH)

@st.cache_resource(show_spinner=False)
def skill_assessment_catalog(file_mtime_ns: int) -> dict[str, Any]:
    """Load the validated static assessment catalogue once per file version."""
    del file_mtime_ns
    return load_skill_assessments(SKILL_ASSESSMENTS_PATH)

@st.cache_resource(show_spinner=False)
def readiness_rules(file_mtime_ns: int) -> dict[str, Any]:
    """Load the validated static readiness rules once per file version."""
    del file_mtime_ns
    return load_readiness_rules(READINESS_RULES_PATH)

def init_state() -> None:
    if "initialized" not in st.session_state:
        saved = load_saved_data(MEMORY_PATH)
        st.session_state.profile, st.session_state.history = saved["profile"], saved["history"]
        st.session_state.remember = False
        st.session_state.initialized = True
    if "demo_profile" not in st.session_state:
        try:
            st.session_state.demo_profile = demo_profile(DEMO_PROFILE_PATH.stat().st_mtime_ns)
            st.session_state.demo_profile_error = ""
        except (OSError, ValueError):
            st.session_state.demo_profile = None
            st.session_state.demo_profile_error = "Demo profile is unavailable; job results will use your search text only."

def save() -> None: save_data(MEMORY_PATH, st.session_state.profile, st.session_state.history, st.session_state.remember)
def format_message_content(content: str) -> str:
    """Build compact escaped paragraphs and numbered lists for chat cards."""
    def safe_line(value: str) -> str:
        parts: list[str] = []
        cursor = 0
        for term in re.finditer(r"\b[A-Za-z][A-Za-z0-9+/#._-]*\b", value):
            parts.append(html.escape(value[cursor:term.start()]))
            parts.append(f'<bdi dir="ltr">{html.escape(term.group(0))}</bdi>')
            cursor = term.end()
        parts.append(html.escape(value[cursor:]))
        return "".join(parts)
    blocks: list[str] = []
    list_items: list[str] = []
    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            blocks.append("<ol>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ol>")
            list_items = []
    for line in content.splitlines():
        match = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
        if match:
            list_items.append(safe_line(match.group(1)))
        elif line.strip():
            flush_list()
            blocks.append(f"<p>{safe_line(line)}</p>")
    flush_list()
    return "".join(blocks) or "<p></p>"

def render_message(role: str, content: str) -> None:
    direction = text_direction(content)
    with st.chat_message(role):
        # Escaped HTML keeps RTL message blocks safe even for untrusted input.
        st.markdown(f'<div class="chat-message-text" dir="{direction}" style="text-align:{"right" if direction == "rtl" else "left"};unicode-bidi:plaintext;line-height:1.55">{format_message_content(content)}</div>', unsafe_allow_html=True)

def match_label(level: str, arabic: bool) -> str:
    labels = {
        "highly_suitable": ("✅ مناسبة جدًا", "✅ Highly suitable"),
        "suitable_small_gap": ("⭐ مناسبة مع فجوة بسيطة", "⭐ Suitable with a small gap"),
        "related_opportunity": ("🔗 فرصة مرتبطة", "🔗 Related opportunity"),
        # Backward-compatible history values from earlier app versions.
        "perfect": ("✅ مناسبة جدًا", "✅ Highly suitable"),
        "good": ("⭐ مناسبة مع فجوة بسيطة", "⭐ Suitable with a small gap"),
        "related": ("🔗 فرصة مرتبطة", "🔗 Related opportunity"),
    }
    return labels.get(level, labels["related_opportunity"])[0 if arabic else 1]

def next_action_text(result: dict[str, Any], arabic: bool) -> str:
    level = result.get("next_action_key", result.get("match_label_key", "related_opportunity"))
    missing = result.get("missing_required_skills", result.get("missing_skills", []))
    if level == "highly_suitable":
        return "مهاراتك الأساسية متوافقة مع متطلبات هذه الوظيفة. راجع التفاصيل ثم افتح رابط التقديم." if arabic else "Your core skills align with this role. Review the details and open the application link."
    if level == "suitable_small_gap" and missing:
        return f"طوّر مهارة {missing[0]} لتصبح أقرب إلى متطلبات الوظيفة." if arabic else f"Strengthen {missing[0]} to become more aligned with this role."
    if missing:
        names = "، ".join(missing[:2]) if arabic else " and ".join(missing[:2])
        return f"هذه الوظيفة قريبة من مسارك، لكنها تحتاج تطوير {names}." if arabic else f"This role is related to your path, but you should strengthen {names}."
    return "راجع متطلبات الوظيفة وحدد خطوة تطوير واحدة قبل التقديم." if arabic else "Review the role requirements and choose one development step before applying."

def job_card_html(result: dict[str, Any], language: str) -> str:
    """Return a self-contained, escaped card with no visible source/demo fields."""
    job, arabic = result["job"], language in {"ar", "mixed"}
    title = job["title_ar"] if arabic else job["title"]
    description = job["description_ar"] if arabic else job["description_en"]
    level = result.get("match_label_key", result.get("match_level", "related_opportunity"))
    matched = result.get("matched_required_skills", [])
    missing = result.get("missing_required_skills", result.get("missing_skills", []))
    missing_nice = result.get("missing_nice_to_have_skills", [])
    matched_label = "مهارات متوافقة" if arabic else "Matched skills"
    missing_label = "مهارات يمكنك تطويرها" if arabic else "Missing required skills"
    nice_label = "مهارات إضافية يمكنك تطويرها" if arabic else "Missing nice-to-have skills"
    empty_label = "لا يوجد" if arabic else "None"
    gap_html = f'<div class="job-card__gap"><p><strong>{html.escape(matched_label)}:</strong> {html.escape(" · ".join(matched) if matched else empty_label)}</p><p><strong>{html.escape(missing_label)}:</strong> {html.escape(" · ".join(missing) if missing else empty_label)}</p>'
    if missing_nice:
        gap_html += f'<p><strong>{html.escape(nice_label)}:</strong> {html.escape(" · ".join(missing_nice))}</p>'
    gap_html += "</div>"
    next_action = next_action_text(result, arabic)
    return f"""
        <article class="job-card" dir="{'rtl' if arabic else 'ltr'}">
          <span class="job-card__match job-card__match--{html.escape(level)}">{html.escape(match_label(level, arabic))}</span>
          <h3 class="job-card__title">{html.escape(title)}</h3>
          <p class="job-card__meta">{html.escape(job['company'])} · {html.escape(job['location'])}</p>
          <p class="job-card__meta"><strong>{html.escape(job['work_mode'])}</strong> · {html.escape(job['employment_type'])} · {html.escape(job['experience_level'])}</p>
          <p class="job-card__skills">{html.escape(' · '.join(job['skills'][:5]))}</p>
          <p class="job-card__description">{html.escape(description)}</p>
          {gap_html}
          <p class="job-card__next">{html.escape(next_action)}</p>
          <a class="job-card__apply" href="{html.escape(job['apply_url'], quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape('قدّم الآن' if arabic else 'Apply now')}</a>
        </article>
        """

def safe_key_part(value: str, separator: str = "-") -> str:
    return re.sub(r"[^a-z0-9]+", separator, value.casefold()).strip(separator) or "item"

def roadmap_anchor_id(job_id: str, skill_name: str) -> str:
    safe_skill = safe_key_part(skill_name)
    safe_job = safe_key_part(job_id)
    return f"roadmap-{safe_job}-{safe_skill}"

def assessment_anchor_id(job_id: str, widget_scope: str) -> str:
    return f"assessment-{safe_key_part(widget_scope)}-{safe_key_part(job_id)}"

def roadmap_html(roadmap: dict[str, Any], language: str, anchor_id: str = "") -> str:
    """Render one escaped bilingual recommendation without automatic actions."""
    arabic = language in {"ar", "mixed"}
    suffix = "ar" if arabic else "en"
    direction = "rtl" if arabic else "ltr"
    labels = {
        "why": "لماذا تهم هذه المهارة" if arabic else "Why this skill matters",
        "time": "الوقت التقديري" if arabic else "Estimated learning time",
        "hours": "ساعات" if arabic else "hours",
        "resource": "مصدر التعلم" if arabic else "Learning resource",
        "no_resource": "لا يوجد رابط محدد؛ استخدم الخطة العامة أدناه." if arabic else "No specific link is available; use the generic plan below.",
        "evidence": "الدليل المطلوب" if arabic else "Evidence required",
        "criteria": "معايير الإكمال" if arabic else "Completion criteria",
    }
    stage_labels = {
        "learn": "تعلّم" if arabic else "Learn",
        "build": "طبّق" if arabic else "Build",
        "evaluate": "قيّم" if arabic else "Evaluate",
        "portfolio": "أضف لملف أعمالك" if arabic else "Portfolio",
    }
    skill = roadmap.get("requested_skill", roadmap.get("skill", ""))
    link = roadmap.get("resource")
    if link:
        resource_html = (
            f'<a href="{html.escape(link["url"], quote=True)}" target="_blank" rel="noopener noreferrer">'
            f'{html.escape(link["title"])} — {html.escape(link["provider"])}</a>'
        )
    else:
        resource_html = html.escape(labels["no_resource"])
    steps = "".join(
        f'<li><strong>{html.escape(stage_labels.get(step.get("stage", ""), step.get("stage", "")))}:</strong> '
        f'{html.escape(step.get(suffix, ""))}</li>'
        for step in roadmap.get("roadmap", [])
    )
    criteria = "".join(f'<li><bdi dir="ltr">{html.escape(value)}</bdi></li>' for value in roadmap.get("completion_criteria", []))
    return f"""
      <section class="roadmap-card"{f' id="{html.escape(anchor_id, quote=True)}"' if anchor_id else ''} dir="{direction}">
        <h4><bdi dir="ltr">{html.escape(skill)}</bdi></h4>
        <p><strong>{html.escape(labels['why'])}:</strong> {html.escape(roadmap.get(f'why_{suffix}', ''))}</p>
        <p><strong>{html.escape(labels['time'])}:</strong> {html.escape(str(roadmap.get('estimated_hours', '—')))} {html.escape(labels['hours'])}</p>
        <p><strong>{html.escape(labels['resource'])}:</strong> {resource_html}</p>
        <ol>{steps}</ol>
        <p><strong>{html.escape(labels['evidence'])}:</strong> {html.escape(roadmap.get(f'evidence_{suffix}', ''))}</p>
        <p><strong>{html.escape(labels['criteria'])}:</strong></p><ul>{criteria}</ul>
      </section>
    """

def assessment_result_html(result: dict[str, Any], catalog: dict[str, Any], language: str, roadmap_anchor: str = "") -> str:
    """Render post-submit scoring and corrections for one skill."""
    arabic = language in {"ar", "mixed"}
    suffix, direction = ("ar", "rtl") if arabic else ("en", "ltr")
    outcome_key = "passed" if result["passed"] else "needs_practice"
    outcome_prefix = ("اجتاز" if result["passed"] else "يحتاج تدريب") if arabic else ("Passed" if result["passed"] else "Needs Practice")
    outcome_detail = catalog["result_labels"][outcome_key][suffix]
    score_label = "النتيجة" if arabic else "Score"
    correct_label = "الإجابة الصحيحة" if arabic else "Correct answer"
    explanation_label = "التوضيح" if arabic else "Explanation"
    note = "هذا تقييم أولي للديمو، وليس شهادة مهنية." if arabic else "This is a preliminary demo assessment, not a professional certification."
    corrections: list[str] = []
    for detail in result["details"]:
        question = detail["question"]
        correct = next(option for option in question["options"] if option["id"] == detail["correct_option_id"])
        corrections.append(
            f'<li><p>{html.escape(question[f"question_{suffix}"])}</p>'
            f'<p><strong>{html.escape(correct_label)}:</strong> {html.escape(correct[suffix])}</p>'
            f'<p><strong>{html.escape(explanation_label)}:</strong> {html.escape(question[f"explanation_{suffix}"])}</p></li>'
        )
    practice_link = ""
    if not result["passed"] and roadmap_anchor:
        link_text = "ارجع إلى خطة سد فجوة المهارات" if arabic else "Review the Mini Skill-Gap Roadmap"
        practice_link = f'<p><a href="#{html.escape(roadmap_anchor, quote=True)}">{html.escape(link_text)}</a></p>'
    state_class = "passed" if result["passed"] else "practice"
    return f"""
      <section class="assessment-result assessment-result--{state_class}" dir="{direction}">
        <h4>{html.escape(result['skill'])}</h4>
        <p><strong>{html.escape(score_label)}:</strong> {result['correct_answers']}/{result['total_questions']} — {result['score_percentage']}%</p>
        <p><strong>{html.escape(outcome_prefix)}:</strong> {html.escape(outcome_detail)}</p>
        <ol>{''.join(corrections)}</ol>
        {practice_link}
        <p><em>{html.escape(note)}</em></p>
      </section>
    """

def render_skill_assessments(
    result: dict[str, Any],
    language: str,
    catalog: dict[str, Any],
    roadmap_available: bool,
    widget_scope: str,
) -> None:
    missing = result.get("missing_required_skills", result.get("missing_skills", []))
    selected = select_assessment_skills(missing, catalog)
    if not selected:
        return
    arabic = language in {"ar", "mixed"}
    suffix = "ar" if arabic else "en"
    job_id = str(result["job"]["id"])
    expander_label = "اختبر مهاراتي" if arabic else "Test My Skills"
    submit_label = "أرسل الإجابات" if arabic else "Submit answers"
    note = "هذا تقييم أولي للديمو، وليس شهادة مهنية." if arabic else "This is a preliminary demo assessment, not a professional certification."
    st.markdown(f'<span id="{html.escape(assessment_anchor_id(job_id, widget_scope), quote=True)}"></span>', unsafe_allow_html=True)
    with st.expander(expander_label):
        st.caption(note)
        for item in selected:
            skill_name, assessment = item["skill"], item["assessment"]
            if assessment is None:
                fallback = catalog["fallback"][suffix]
                st.info(f"{skill_name}: {fallback}")
                continue
            safe_skill = safe_key_part(skill_name, "_")
            form_key = f"assessment_form__{widget_scope}__{job_id}__{safe_skill}"
            answers_key = f"assessment_answers__{widget_scope}__{job_id}__{safe_skill}"
            result_key = f"assessment_result__{widget_scope}__{job_id}__{safe_skill}"
            answers: dict[str, str | None] = {}
            with st.form(form_key):
                st.markdown(f"#### {html.escape(skill_name)}")
                for question in assessment_questions(assessment, catalog):
                    option_text = {option["id"]: option[suffix] for option in question["options"]}
                    widget_key = f"assessment__{widget_scope}__{job_id}__{safe_skill}__{question['id']}"
                    answers[question["id"]] = st.radio(
                        question[f"question_{suffix}"],
                        list(option_text),
                        format_func=lambda option_id, labels=option_text: labels[option_id],
                        index=None,
                        key=widget_key,
                    )
                submitted = st.form_submit_button(submit_label)
            if submitted:
                st.session_state[answers_key] = dict(answers)
                st.session_state[result_key] = calculate_assessment_result(
                    assessment,
                    answers,
                    catalog["assessment_rules"]["passing_score_percentage"],
                    catalog["assessment_rules"]["questions_per_skill"],
                )
            stored_result = st.session_state.get(result_key)
            if stored_result:
                anchor = roadmap_anchor_id(job_id, skill_name) if roadmap_available else ""
                st.markdown(assessment_result_html(stored_result, catalog, language, anchor), unsafe_allow_html=True)

def current_assessment_results(result: dict[str, Any], catalog: dict[str, Any], widget_scope: str) -> list[dict[str, Any]]:
    """Read only this card's completed required-skill assessments from session state."""
    job_id = str(result["job"]["id"])
    completed: list[dict[str, Any]] = []
    for item in select_assessment_skills(result.get("missing_required_skills", []), catalog):
        safe_skill = safe_key_part(item["skill"], "_")
        key = f"assessment_result__{widget_scope}__{job_id}__{safe_skill}"
        stored = st.session_state.get(key)
        if isinstance(stored, dict):
            completed.append(stored)
    return completed

def readiness_card_html(
    readiness: dict[str, Any],
    job: dict[str, Any],
    rules: dict[str, Any],
    language: str,
    roadmap_anchor: str,
    assessment_anchor: str,
) -> str:
    """Render one bilingual readiness result using only validated rule content."""
    arabic = language in {"ar", "mixed"}
    suffix, direction = ("ar", "rtl") if arabic else ("en", "ltr")
    status = readiness["status"]
    display_labels = rules["display"]["labels"]
    score_label = display_labels[f"readiness_score_{suffix}"]
    job_label = display_labels[f"job_match_{suffix}"]
    assessment_label = display_labels[f"assessment_{suffix}"]
    strengths_label = display_labels[f"strengths_{suffix}"]
    gaps_label = display_labels[f"gaps_{suffix}"]
    next_label = display_labels[f"next_action_{suffix}"]
    none_text = "لا يوجد" if arabic else "None"
    strengths = "".join(f"<li>{html.escape(skill)}</li>" for skill in readiness["strengths"]) or f"<li>{none_text}</li>"
    gaps = "".join(f"<li>{html.escape(skill)}</li>" for skill in readiness["priority_gaps"]) or f"<li>{none_text}</li>"
    weights = rules["score"]["weights"]
    job_weight, assessment_weight = round(weights["job_match_score"] * 100), round(weights["skill_assessment_score"] * 100)
    formula = (
        f"{job_weight}% مطابقة الوظيفة + {assessment_weight}% اختبار المهارات"
        if arabic else f"{job_weight}% Job Match + {assessment_weight}% Skill Assessment"
    )
    readiness_value = "—" if readiness["readiness_score"] is None else f'{readiness["readiness_score"]}%'
    assessment_value = "—" if readiness["skill_assessment_score"] is None else f'{readiness["skill_assessment_score"]}%'
    gates = "".join(
        f'<p class="readiness-card__gate">{html.escape(gate[f"message_{suffix}"])}</p>'
        for gate in readiness.get("applied_gates", [])
    )
    action = readiness["action"]
    action_id = status["primary_action"]
    if action_id == "view_job":
        action_href = job["apply_url"]
        action_attributes = ' target="_blank" rel="noopener noreferrer"'
    elif action_id in {"review_roadmap", "start_roadmap"} and roadmap_anchor:
        action_href, action_attributes = f"#{roadmap_anchor}", ""
    else:
        action_href, action_attributes = f"#{assessment_anchor}", ""
    assessment_return = ""
    if action_id == "review_roadmap":
        return_label = "العودة إلى اختبار المهارات" if arabic else "Return to Skill Assessment"
        assessment_return = f'<p><a href="#{html.escape(assessment_anchor, quote=True)}">{html.escape(return_label)}</a></p>'
    job_link_label = "رابط الوظيفة" if arabic else "Job link"
    return f"""
      <section class="readiness-card" dir="{direction}">
        <h4>{html.escape(status['icon'])} {html.escape(status[f'label_{suffix}'])}</h4>
        <p>{html.escape(status[f'summary_{suffix}'])}</p>
        <p><strong>{html.escape(score_label)}:</strong> {readiness_value}</p>
        <p class="readiness-card__formula">{html.escape(formula)}</p>
        <p><strong>{html.escape(job_label)}:</strong> {readiness['job_match_score']}%</p>
        <p><strong>{html.escape(assessment_label)}:</strong> {assessment_value}</p>
        <p><strong>{html.escape(strengths_label)}:</strong></p><ul>{strengths}</ul>
        <p><strong>{html.escape(gaps_label)}:</strong></p><ul>{gaps}</ul>
        {gates}
        <p><strong>{html.escape(next_label)}:</strong> {html.escape(action[f'instruction_{suffix}'])}</p>
        <p><a href="{html.escape(action_href, quote=True)}"{action_attributes}>{html.escape(action[f'label_{suffix}'])}</a></p>
        {assessment_return}
        <p><a href="{html.escape(job['apply_url'], quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(job_link_label)}</a></p>
        <p><em>{html.escape(readiness['disclaimer'][suffix])}</em></p>
      </section>
    """

def render_final_readiness(
    result: dict[str, Any],
    language: str,
    assessment_catalog: dict[str, Any],
    rules: dict[str, Any],
    widget_scope: str,
) -> None:
    missing = result.get("missing_required_skills", result.get("missing_skills", []))
    matched = result.get("matched_required_skills", [])
    completed = current_assessment_results(result, assessment_catalog, widget_scope)
    calculated = calculate_readiness(result.get("score"), missing, matched, completed, rules)
    job_id = str(result["job"]["id"])
    st.session_state[f"readiness_result__{widget_scope}__{job_id}"] = calculated
    label = rules["title_ar"] if language in {"ar", "mixed"} else rules["title_en"]
    first_gap = missing[0] if missing else "skill"
    with st.expander(label):
        st.markdown(
            readiness_card_html(
                calculated,
                result["job"],
                rules,
                language,
                roadmap_anchor_id(job_id, first_gap),
                assessment_anchor_id(job_id, widget_scope),
            ),
            unsafe_allow_html=True,
        )

def render_job_cards(
    results: list[dict[str, Any]],
    language: str,
    catalog: dict[str, Any] | None = None,
    assessments: dict[str, Any] | None = None,
    readiness: dict[str, Any] | None = None,
    widget_scope: str = "current",
) -> None:
    """Render structured cards; result data keeps the language-neutral match level."""
    for result_index, result in enumerate(results):
        st.markdown(job_card_html(result, language), unsafe_allow_html=True)
        if catalog:
            roadmaps = build_skill_roadmaps(
                result.get("missing_required_skills", result.get("missing_skills", [])),
                catalog,
                result.get("missing_nice_to_have_skills", []),
            )
            if roadmaps:
                label = "خطة قصيرة لسد فجوة المهارات" if language in {"ar", "mixed"} else "Mini Skill-Gap Roadmap"
                with st.expander(label):
                    for roadmap in roadmaps:
                        anchor = roadmap_anchor_id(str(result["job"]["id"]), roadmap["requested_skill"])
                        st.markdown(roadmap_html(roadmap, language, anchor), unsafe_allow_html=True)
        card_scope = f"{widget_scope}_{result_index}"
        if assessments:
            render_skill_assessments(result, language, assessments, catalog is not None, card_scope)
        if assessments and readiness:
            render_final_readiness(result, language, assessments, readiness, card_scope)

def fast_clarification(message: str, profile: dict[str, str]) -> str:
    """Immediate fallback that never waits for a generative model."""
    if detect_language(message) in {"ar", "mixed"}:
        target = profile.get("target_roles", "")
        known = f" أعرف أن هدفك هو {target}." if target else ""
        return f"أقدر أساعدك في CV وLinkedIn والوظائف والمقابلات والعمل عن بُعد.{known}\n\nلإجابة أدق، اكتب: الدور المستهدف | مستوى الخبرة | المشكلة المحددة."
    return "I can help with CVs, LinkedIn, job search, interviews, and remote work. Send: target role | experience level | specific problem."

def main() -> None:
    init_state()
    inject_styles()
    try: kb, retriever = services()
    except Exception as exc:
        st.error(f"Knowledge base could not start: {exc}"); st.stop()
    try:
        catalog = learning_catalog(LEARNING_RESOURCES_PATH.stat().st_mtime_ns)
        catalog_error = ""
    except (OSError, ValueError):
        catalog, catalog_error = None, "Learning roadmaps are temporarily unavailable. Job search still works normally."
    try:
        assessments = skill_assessment_catalog(SKILL_ASSESSMENTS_PATH.stat().st_mtime_ns)
        assessment_error = ""
    except (OSError, ValueError):
        assessments, assessment_error = None, "Skill verification is temporarily unavailable. Job search still works normally."
    try:
        readiness = readiness_rules(READINESS_RULES_PATH.stat().st_mtime_ns)
        readiness_error = ""
    except (OSError, ValueError):
        readiness, readiness_error = None, "Final readiness is temporarily unavailable. Job search still works normally."
    st.markdown("""
    <section class="tap-hero">
      <h1>💼 TAP Career Companion</h1>
      <p dir="rtl">رفيقك المهني المحلي — خطوات عملية لمسارك المهني</p>
      <span class="tap-badge">Local · Private · Fast answers</span>
    </section>
    """, unsafe_allow_html=True)
    with st.sidebar:
        st.header("Demo Profile | الملف التجريبي")
        candidate = st.session_state.demo_profile
        if candidate:
            personal = candidate["personal_information"]
            career = candidate["career_profile"]
            preferences = candidate["work_preferences"]
            st.subheader(personal.get("display_name", "Candidate"))
            st.caption(f"{career.get('target_role', '—')} · {career.get('experience_level', '—')}")
            st.caption(f"{personal.get('city', '—')}, {personal.get('country', '—')}")
            st.caption("Work: " + ", ".join(preferences.get("preferred_modes", [])))
            st.caption("Skills: " + ", ".join(candidate.get("skills", [])[:6]))
        else:
            st.warning(st.session_state.demo_profile_error)
        if catalog_error:
            st.caption(catalog_error)
        if assessment_error:
            st.caption(assessment_error)
        if readiness_error:
            st.caption(readiness_error)
        st.session_state.remember = st.toggle("Remember me on this device", value=st.session_state.remember)
        st.divider()
        if st.button("New Chat", use_container_width=True): st.session_state.history = []; save(); st.rerun()
        if st.button("Delete Saved Data", use_container_width=True):
            delete_saved_data(MEMORY_PATH); st.session_state.profile = empty_profile(); st.session_state.history = []; st.success("Saved local profile and conversation deleted.")
    for message_index, message in enumerate(st.session_state.history):
        render_message(message["role"], message["content"])
        if message.get("jobs"):
            render_job_cards(message["jobs"], message.get("job_language", "en"), catalog, assessments, readiness, f"history_{message_index}")
    user_message = st.chat_input("Ask about your career… | اسأل عن مسارك المهني…")
    if not user_message: return
    st.session_state.history.append({"role":"user", "content":user_message}); render_message("user", user_message)
    language = detect_language(user_message)
    if is_job_search_intent(user_message):
        try:
            matches = job_index(JOBS_PATH.stat().st_mtime_ns).search(user_message, st.session_state.demo_profile)
        except (OSError, ValueError) as exc:
            answer = f"تعذر فتح فرص العمل المحلية: {exc}" if language in {"ar", "mixed"} else f"Could not load local jobs: {exc}"
            st.session_state.history.append({"role":"assistant", "content":answer}); render_message("assistant", answer); save(); return
        if matches:
            answer = "لقيتلك فرص قريبة من طلبك:" if language in {"ar", "mixed"} else "I found opportunities matching your request:"
            event = {"role":"assistant", "content":answer, "jobs":matches, "job_language":language}
            st.session_state.history.append(event)
            render_message("assistant", answer)
            render_job_cards(matches, language, catalog, assessments, readiness, f"history_{len(st.session_state.history) - 1}")
            save(); return
        answer = "ما لقيت تطابقًا كافيًا. جرّب إزالة الموقع، اختيار Remote، أو استخدام مسمى أوسع." if language in {"ar", "mixed"} else "No close match found. Try removing the location, choosing Remote, or using a broader role title."
        st.session_state.history.append({"role":"assistant", "content":answer}); render_message("assistant", answer); save(); return
    if is_underspecified_job_request(user_message):
        answer = (
            "شو الدور المستهدف ومستوى خبرتك؟ مثال: Junior Backend Developer | مبتدئ."
            if language in {"ar", "mixed"}
            else "What target role and experience level should I use? Example: Junior Backend Developer | entry level."
        )
        st.session_state.history.append({"role":"assistant", "content":answer})
        render_message("assistant", answer); save(); return
    typed_option = find_typed_assessment_option(user_message, assessments) if assessments else None
    if typed_option:
        answer = (
            f"هذه إجابة من اختبار {typed_option['skill']}. حتى تنحسب نتيجتك، افتح بطاقة الوظيفة ثم «اختبر مهاراتي»، اختر الإجابة داخل النموذج، واضغط «أرسل الإجابات». لن أصحح إجابات الاختبار داخل الشات قبل الإرسال."
            if language in {"ar", "mixed"}
            else f"This looks like an answer from the {typed_option['skill']} assessment. To record your score, open the job card, choose it inside “Test My Skills,” and submit the form. Assessment answers are not graded in chat before submission."
        )
        st.session_state.history.append({"role":"assistant", "content":answer})
        render_message("assistant", answer); save(); return
    if is_roadmap_ui_request(user_message):
        answer = (
            "لفتح الخطة: ابحث أولًا عن وظيفة محددة، ثم افتح «خطة قصيرة لسد فجوة المهارات» تحت بطاقة الوظيفة. الخطة تُبنى من المهارات المطلوبة الناقصة لتلك الوظيفة، لذلك لا تظهر كإجابة عامة منفصلة."
            if language in {"ar", "mixed"}
            else "To open the roadmap, search for a specific job first, then expand “Mini Skill-Gap Roadmap” beneath its card. The roadmap is built from that job’s missing required skills."
        )
        st.session_state.history.append({"role":"assistant", "content":answer})
        render_message("assistant", answer); save(); return
    try:
        indexed_jobs = [item.job for item in job_index(JOBS_PATH.stat().st_mtime_ns).index]
        role_fragment = find_role_fragment(user_message, indexed_jobs)
    except (OSError, ValueError):
        role_fragment = None
    if role_fragment:
        role_name = role_fragment["title_ar"] if language in {"ar", "mixed"} else role_fragment["title"]
        answer = (
            f"تمام، فهمت المجال الذي تستهدفه. أقرب دور متوفر في بيانات الديمو هو {role_name}. اكتب طلبًا واحدًا محددًا: «اعرضلي وظائف مناسبة»، أو «ما المهارات المطلوبة؟»، أو «كيف أخصص CV لهذا الدور؟»."
            if language in {"ar", "mixed"}
            else f"Got it — the closest role in the demo data is {role_name}. Choose one request: “show matching jobs,” “what skills are required?”, or “how should I tailor my CV for this role?”"
        )
        st.session_state.history.append({"role":"assistant", "content":answer})
        render_message("assistant", answer); save(); return
    special = boundary_response(user_message)
    retrieved = retriever.search(user_message, threshold=FAST_MATCH_THRESHOLD)
    if special: answer = special
    elif retrieved:
        # Known TAP topics return instantly without embeddings or Ollama generation.
        answer = instant_answer(retrieved[0], language, st.session_state.profile, user_message)
    else:
        answer = fast_clarification(user_message, st.session_state.profile)
    render_message("assistant", answer)
    st.session_state.history.append({"role":"assistant", "content":answer}); save()
    if any(r["item"]["category"].startswith("tap") or r["item"]["intent"].startswith("tap_") for r in retrieved):
        refs = [ref for r in retrieved for ref in r["item"].get("source_refs", [])]
        if refs:
            with st.expander("Source"): st.write("\n".join(refs))
if __name__ == "__main__": main()
