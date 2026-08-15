from __future__ import annotations
import html
import re
from typing import Any
import streamlit as st
from src.config import AGENT_FLOW_PATH, COMPANION_ASSET_PATH, DEMO_PROFILE_PATH, FAST_MATCH_THRESHOLD, JOBS_PATH, KB_PATH, LEARNING_RESOURCES_PATH, MEMORY_PATH, READINESS_RULES_PATH, SKILL_ASSESSMENTS_PATH
from src.data_loader import load_agent_flow, load_demo_profile, load_knowledge_base, load_learning_resources, load_readiness_rules, load_skill_assessments
from src.language import detect_language, text_direction
from src.memory import delete_saved_data, empty_profile, load_saved_data, save_data
from src.fast_matcher import FastMatcher, instant_answer
from src.job_search import JobSearchIndex, LocalJobProvider, is_job_search_intent, is_underspecified_job_request
from src.learning_roadmap import build_skill_roadmaps
from src.skill_assessment import assessment_questions, calculate_assessment_result, find_skill_assessment, select_assessment_skills
from src.readiness import calculate_readiness
from src.career_agent import build_agent_context, build_message_signature, get_companion_visual, get_current_stage_progress, get_localized_action, initialize_agent_state, reset_job_dependent_state, resolve_agent_message, transition_agent_state
from src.chat_routing import find_role_fragment, find_typed_assessment_option, is_roadmap_ui_request
from src.safety import boundary_response

st.set_page_config(page_title="TAP Career Companion", page_icon="💼", layout="centered")

def inject_styles() -> None:
    """Static visual styling; user content is never interpolated here."""
    st.markdown("""
    <style>
      .stApp { background: #f6f8fc; }
      .block-container { max-width: 1320px; padding-top: 2rem; padding-bottom: 6rem; }
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
      .tap-companion-title { margin:.15rem 0 .25rem; color:#123b5b; font-size:1.2rem; font-weight:800; }
      .tap-companion-role { color:#0e7490; font-size:.82rem; font-weight:700; margin-bottom:.65rem; }
      .tap-companion-stage { display:inline-block; background:#e0f2fe; color:#075985; border-radius:999px; padding:.2rem .55rem; font-size:.76rem; font-weight:750; }
      .tap-companion-bubble { background:#f4f8fa; color:#162c42; border:1px solid #d9e4ee; border-radius:14px 14px 14px 4px; padding:.75rem .8rem; margin:.7rem 0; line-height:1.55; }
      .tap-journey { margin:.75rem 0; }
      .tap-journey-step { display:flex; align-items:center; gap:.5rem; position:relative; padding:.22rem 0; color:#64748b; }
      .tap-journey-step::before { content:""; width:3px; height:100%; background:#d9e4ea; position:absolute; inset-inline-start:.7rem; top:1.15rem; transition:background-color 600ms ease; }
      .tap-journey-step:last-child::before { display:none; }
      .tap-journey-dot { width:1.45rem; height:1.45rem; border-radius:50%; display:flex; align-items:center; justify-content:center; z-index:1; background:#d9e4ea; font-size:.72rem; }
      .tap-journey-label { font-size:.78rem; font-weight:650; }
      .tap-journey-step--completed .tap-journey-dot { background:#16a3a8; color:white; }
      .tap-journey-step--completed .tap-journey-label { color:#0f766e; }
      .tap-journey-step--active .tap-journey-dot { background:#0b5e8e; color:white; box-shadow:0 0 0 4px #dbeafe; transform:scale(1.05); }
      .tap-journey-step--active .tap-journey-label { color:#0b5e8e; font-weight:800; }
      .tap-journey-step--completed::before { background:#16a3a8; }
      .tap-action-hint { border:1px dashed #7aa8be; border-radius:10px; padding:.5rem .6rem; color:#29455c; text-align:center; font-size:.82rem; font-weight:700; }
      .tap-selected { background:#ecfeff; border:1px solid #67e8f9; border-radius:10px; padding:.4rem .55rem; color:#155e75; font-size:.8rem; font-weight:700; }
      [data-testid="stChatInput"] { border-radius:16px; border:1px solid #b9c9d8; box-shadow:0 7px 22px rgba(28,57,86,.10); }
      .stButton > button { border-radius:10px; border:1px solid #7aa8be; font-weight:600; }
      @media (prefers-reduced-motion:reduce) { .tap-journey-step::before, .tap-journey-dot { transition:none !important; animation:none !important; } }
      @media (max-width:760px) { .block-container { padding:1rem .8rem 5rem; } .tap-hero { padding:1.2rem; border-radius:16px; } .tap-hero h1 { font-size:1.55rem; } [data-testid="stHorizontalBlock"] { flex-direction:column-reverse; } }
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

@st.cache_resource(show_spinner=False)
def agent_flow(file_mtime_ns: int) -> dict[str, Any]:
    """Load the validated, read-only TAP Companion flow once per file version."""
    del file_mtime_ns
    return load_agent_flow(AGENT_FLOW_PATH)

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

def clear_job_widget_state(job_id: str) -> None:
    """Remove only downstream Streamlit values scoped to one previously selected job."""
    token = f"__{job_id}__"
    prefixes = ("assessment__", "assessment_answers__", "assessment_result__", "readiness_result__")
    for key in list(st.session_state):
        if isinstance(key, str) and key.startswith(prefixes) and (token in key or key.endswith(f"__{job_id}")):
            del st.session_state[key]

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
    flow: dict[str, Any] | None = None,
) -> None:
    missing = result.get("missing_required_skills", result.get("missing_skills", []))
    selected = select_assessment_skills(missing, catalog)
    agent = st.session_state.get("tap_agent")
    if flow and isinstance(agent, dict) and agent.get("selected_job_id") == str(result["job"]["id"]):
        selected = selected[:1]
    if not selected:
        return
    arabic = language in {"ar", "mixed"}
    suffix = "ar" if arabic else "en"
    job_id = str(result["job"]["id"])
    expander_label = "اختبر مهاراتي" if arabic else "Test My Skills"
    submit_label = "أرسل الإجابات" if arabic else "Submit answers"
    note = "هذا تقييم أولي للديمو، وليس شهادة مهنية." if arabic else "This is a preliminary demo assessment, not a professional certification."
    st.markdown(f'<span id="{html.escape(assessment_anchor_id(job_id, widget_scope), quote=True)}"></span>', unsafe_allow_html=True)
    assessment_open = st.session_state.get("tap_agent_open_assessment") == job_id
    with st.expander(expander_label, expanded=assessment_open):
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
                agent = st.session_state.get("tap_agent")
                if flow and isinstance(agent, dict) and agent.get("selected_job_id") == job_id:
                    stored = st.session_state[result_key]
                    by_job = dict(agent.get("assessment_results_by_job", {}))
                    job_results = dict(by_job.get(job_id, {}))
                    job_results[skill_name] = stored
                    by_job[job_id] = job_results
                    agent["assessment_results_by_job"] = by_job
                    agent["latest_assessment"] = stored
                    if agent.get("current_state") != "assessment_pending":
                        agent["current_state"] = "assessment_pending"
                        agent["current_stage"] = "verify"
                    st.session_state.tap_agent = transition_agent_state(
                        agent,
                        "assessment_submitted",
                        {"assessment_passed": bool(stored.get("passed"))},
                        flow,
                    )
                    st.rerun()
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
    flow: dict[str, Any] | None = None,
) -> None:
    """Render structured cards; result data keeps the language-neutral match level."""
    for result_index, result in enumerate(results):
        st.markdown(job_card_html(result, language), unsafe_allow_html=True)
        job_id = str(result["job"]["id"])
        agent = st.session_state.get("tap_agent")
        selected = isinstance(agent, dict) and agent.get("selected_job_id") == job_id
        select_label = "✓ الوظيفة المختارة" if selected and language in {"ar", "mixed"} else (
            "✓ Selected opportunity" if selected else ("اختر هذه الفرصة" if language in {"ar", "mixed"} else "Select this opportunity")
        )
        if selected:
            st.markdown(f'<div class="tap-selected">{html.escape(select_label)}</div>', unsafe_allow_html=True)
        elif flow and st.button(select_label, key=f"select_job__{widget_scope}__{result_index}__{safe_key_part(job_id, '_')}", use_container_width=True):
            previous_job_id = st.session_state.tap_agent.get("selected_job_id")
            if previous_job_id and previous_job_id != job_id:
                clear_job_widget_state(str(previous_job_id))
            updated = reset_job_dependent_state(st.session_state.tap_agent, job_id, result)
            updated["selected_widget_scope"] = f"{widget_scope}_{result_index}"
            updated = transition_agent_state(updated, "job_selected_or_changed", {"selected_job_id_is_valid": True}, flow)
            st.session_state.tap_agent = updated
            st.rerun()
        show_downstream = flow is None or selected
        if catalog and show_downstream:
            roadmaps = build_skill_roadmaps(
                result.get("missing_required_skills", result.get("missing_skills", [])),
                catalog,
                result.get("missing_nice_to_have_skills", []),
            )
            if roadmaps:
                label = "خطة قصيرة لسد فجوة المهارات" if language in {"ar", "mixed"} else "Mini Skill-Gap Roadmap"
                roadmap_open = selected and st.session_state.get("tap_agent_open_roadmap") == job_id
                with st.expander(label, expanded=roadmap_open):
                    for roadmap in roadmaps:
                        anchor = roadmap_anchor_id(str(result["job"]["id"]), roadmap["requested_skill"])
                        st.markdown(roadmap_html(roadmap, language, anchor), unsafe_allow_html=True)
        card_scope = f"{widget_scope}_{result_index}"
        if assessments and show_downstream:
            render_skill_assessments(result, language, assessments, catalog is not None, card_scope, flow)
        if assessments and readiness and show_downstream:
            render_final_readiness(result, language, assessments, readiness, card_scope)

def fast_clarification(message: str, profile: dict[str, str]) -> str:
    """Immediate fallback that never waits for a generative model."""
    if detect_language(message) in {"ar", "mixed"}:
        target = profile.get("target_roles", "")
        known = f" أعرف أن هدفك هو {target}." if target else ""
        return f"أقدر أساعدك في CV وLinkedIn والوظائف والمقابلات والعمل عن بُعد.{known}\n\nلإجابة أدق، اكتب: الدور المستهدف | مستوى الخبرة | المشكلة المحددة."
    return "I can help with CVs, LinkedIn, job search, interviews, and remote work. Send: target role | experience level | specific problem."

def _agent_selected_result(agent: dict[str, Any]) -> dict[str, Any] | None:
    selected = agent.get("selected_job_match")
    return selected if isinstance(selected, dict) and isinstance(selected.get("job"), dict) else None

def _valid_job_url(result: dict[str, Any] | None) -> bool:
    url = result.get("job", {}).get("apply_url", "") if result else ""
    return isinstance(url, str) and url.startswith(("https://", "http://"))

def handle_companion_action(
    action_id: str,
    flow: dict[str, Any],
    catalog: dict[str, Any] | None,
    assessments: dict[str, Any] | None,
    readiness_rules_data: dict[str, Any] | None,
) -> None:
    """Connect Companion actions to existing deterministic project helpers."""
    agent = dict(st.session_state.tap_agent)
    selected = _agent_selected_result(agent)
    job_id = str(agent.get("selected_job_id") or "")
    if action_id == "analyze_skill_gap" and selected:
        missing = list(selected.get("missing_required_skills", selected.get("missing_skills", [])))
        agent["skill_gap"] = {
            "matched_required_skills": list(selected.get("matched_required_skills", [])),
            "missing_required_skills": missing,
            "missing_nice_to_have_skills": list(selected.get("missing_nice_to_have_skills", [])),
        }
        agent = transition_agent_state(agent, "skill_gap_calculated", {"missing_required_skills_count": len(missing)}, flow)
    elif action_id in {"open_roadmap", "review_current_roadmap"} and selected and catalog:
        roadmaps = build_skill_roadmaps(
            selected.get("missing_required_skills", selected.get("missing_skills", [])),
            catalog,
            selected.get("missing_nice_to_have_skills", []),
        )
        agent["selected_roadmaps"] = roadmaps
        st.session_state.tap_agent_open_roadmap = job_id
        agent = transition_agent_state(agent, "roadmap_opened", {"roadmap_available": bool(roadmaps)}, flow)
    elif action_id == "start_assessment" and selected and assessments:
        priority = None
        if agent.get("selected_roadmaps"):
            priority = agent["selected_roadmaps"][0].get("requested_skill")
        if not priority:
            priority = (selected.get("missing_required_skills") or [None])[0]
        available = bool(priority and find_skill_assessment(str(priority), assessments))
        if available:
            st.session_state.tap_agent_open_assessment = job_id
            agent = transition_agent_state(agent, "assessment_started", {"assessment_available": True}, flow)
        else:
            suffix = "ar" if st.session_state.get("agent_language") in {"ar", "mixed"} else "en"
            st.session_state.tap_agent_notice = assessments.get("fallback", {}).get(suffix, "No assessment is available for this skill.")
    elif action_id == "calculate_readiness" and selected and readiness_rules_data:
        completed = list(agent.get("assessment_results_by_job", {}).get(job_id, {}).values())
        calculated = calculate_readiness(
            selected.get("score"),
            list(selected.get("missing_required_skills", selected.get("missing_skills", []))),
            list(selected.get("matched_required_skills", [])),
            completed,
            readiness_rules_data,
        )
        by_job = dict(agent.get("readiness_result_by_job", {}))
        by_job[job_id] = calculated
        agent["readiness_result_by_job"] = by_job
        agent = transition_agent_state(agent, "readiness_calculated", {"readiness_result_is_valid": calculated.get("state") == "calculated"}, flow)
    elif action_id == "follow_readiness_action" and selected:
        result = agent.get("readiness_result_by_job", {}).get(job_id, {})
        agent = transition_agent_state(
            agent,
            "readiness_action_requested",
            {"readiness_status_id": result.get("status_id"), "selected_job_url_is_valid": _valid_job_url(selected)},
            flow,
        )
        if agent.get("current_state") == "gap_analyzed":
            st.session_state.tap_agent_open_roadmap = job_id
    elif action_id == "retry_data_load":
        st.cache_resource.clear()
    st.session_state.tap_agent = agent

def journey_track_html(agent: dict[str, Any], flow: dict[str, Any], language: str) -> str:
    arabic = language in {"ar", "mixed"}
    suffix = "ar" if arabic else "en"
    steps = []
    for stage in get_current_stage_progress(agent, flow):
        status_text = {"completed": "مكتملة" if arabic else "Completed", "active": "الحالية" if arabic else "Current", "pending": "قادمة" if arabic else "Upcoming"}[stage["status"]]
        label = stage[f"label_{suffix}"]
        steps.append(
            f'<div class="tap-journey-step tap-journey-step--{stage["status"]}">'
            f'<span class="tap-journey-dot" aria-hidden="true">{html.escape(stage["icon"])}</span>'
            f'<span class="tap-journey-label">{html.escape(label)} · {html.escape(status_text)}</span></div>'
        )
    return f'<div class="tap-journey" dir="{"rtl" if arabic else "ltr"}">{"".join(steps)}</div>'

def render_companion(
    flow: dict[str, Any],
    catalog: dict[str, Any] | None,
    assessments: dict[str, Any] | None,
    readiness_rules_data: dict[str, Any] | None,
) -> None:
    agent = st.session_state.tap_agent
    language = st.session_state.get("agent_language", "en")
    arabic = language in {"ar", "mixed"}
    suffix = "ar" if arabic else "en"
    selected = _agent_selected_result(agent)
    job_id = str(agent.get("selected_job_id") or "")
    readiness_result = agent.get("readiness_result_by_job", {}).get(job_id)
    context = build_agent_context(
        st.session_state.get("demo_profile"),
        agent.get("current_job_results"),
        selected,
        agent.get("selected_roadmaps"),
        agent.get("latest_assessment"),
        readiness_result,
        readiness_rules_data,
        language,
    )
    message = resolve_agent_message(agent["current_state"], context, flow, language)
    signature = build_message_signature(agent["current_state"], agent.get("selected_job_id"), message, context)
    if agent.get("last_agent_message_signature") != signature:
        agent = dict(agent)
        agent["last_agent_message_signature"] = signature
        st.session_state.tap_agent = agent
    state_definition = next(item for item in flow["states"] if item["id"] == agent["current_state"])
    stage = flow["journey"]["stages"][agent["current_stage"]]
    visual = get_companion_visual(COMPANION_ASSET_PATH, flow, language)
    with st.container(border=True):
        if visual["kind"] == "image":
            st.image(visual["value"], width=150)
        else:
            st.markdown(f"## {html.escape(visual['value'])}")
            st.caption(visual["label"])
        role = flow["agent"][f"role_{suffix}"]
        stage_label = stage[f"label_{suffix}"]
        badge = flow["ui"]["visual_state_badges"].get(state_definition["visual_state"], "🧭")
        st.markdown(
            f'<div dir="{"rtl" if arabic else "ltr"}"><div class="tap-companion-title">TAP Companion</div>'
            f'<div class="tap-companion-role">{html.escape(role)}</div>'
            f'<span class="tap-companion-stage">{html.escape(badge)} {html.escape(stage_label)}</span>'
            f'<div class="tap-companion-bubble">{message}</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(journey_track_html(agent, flow, language), unsafe_allow_html=True)
        notice = st.session_state.pop("tap_agent_notice", None)
        if notice:
            st.info(notice)
        action = get_localized_action(agent["current_state"], flow, language)
        interrupted = st.session_state.get("tap_agent_interrupted", False)
        if interrupted and agent["current_state"] not in {"profile_loaded", "clarification_needed", "data_unavailable"}:
            continue_action = flow["actions"]["continue_journey"][f"label_{suffix}"]
            if st.button(continue_action, key="tap_agent_continue", use_container_width=True):
                st.session_state.tap_agent_interrupted = False
                st.rerun()
            return
        if not action:
            return
        represented_elsewhere = action["id"] in {"focus_chat_input", "select_job", "submit_assessment"}
        if represented_elsewhere:
            st.markdown(f'<div class="tap-action-hint">{html.escape(action["label"])}</div>', unsafe_allow_html=True)
        elif action["id"] == "view_job_link" and selected and _valid_job_url(selected):
            st.link_button(action["label"], selected["job"]["apply_url"], use_container_width=True)
        elif st.button(action["label"], key=f'tap_agent_action__{action["id"]}__{safe_key_part(job_id, "_")}', use_container_width=True):
            handle_companion_action(action["id"], flow, catalog, assessments, readiness_rules_data)
            st.rerun()

def main() -> None:
    init_state()
    inject_styles()
    try: kb, retriever = services()
    except Exception as exc:
        st.error(f"Knowledge base could not start: {exc}"); st.stop()
    try:
        flow_data = agent_flow(AGENT_FLOW_PATH.stat().st_mtime_ns)
        flow_error = ""
        if "tap_agent" not in st.session_state:
            st.session_state.tap_agent = initialize_agent_state(flow_data)
        if "agent_language" not in st.session_state:
            st.session_state.agent_language = "en"
    except (OSError, ValueError) as exc:
        flow_data, flow_error = None, f"TAP Companion is temporarily unavailable: {exc}"
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
    if flow_data and (catalog_error or assessment_error or readiness_error or st.session_state.demo_profile_error):
        st.session_state.tap_agent = transition_agent_state(
            st.session_state.tap_agent,
            "required_runtime_data_failed",
            {"validated_loader_error_exists": True},
            flow_data,
        )
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
        if flow_error:
            st.caption(flow_error)
        st.session_state.remember = st.toggle("Remember me on this device", value=st.session_state.remember)
        st.divider()
        if st.button("New Chat", use_container_width=True):
            st.session_state.history = []
            if flow_data:
                st.session_state.tap_agent = initialize_agent_state(flow_data)
                st.session_state.tap_agent_interrupted = False
            save(); st.rerun()
        if st.button("Delete Saved Data", use_container_width=True):
            delete_saved_data(MEMORY_PATH); st.session_state.profile = empty_profile(); st.session_state.history = []
            if flow_data:
                st.session_state.tap_agent = initialize_agent_state(flow_data)
            st.success("Saved local profile and conversation deleted.")
    chat_col, companion_col = st.columns([0.68, 0.32], gap="large")
    with companion_col:
        if flow_data:
            render_companion(flow_data, catalog, assessments, readiness)
        else:
            st.info(flow_error)
    with chat_col:
        for message_index, message in enumerate(st.session_state.history):
            render_message(message["role"], message["content"])
            if message.get("jobs"):
                render_job_cards(message["jobs"], message.get("job_language", "en"), catalog, assessments, readiness, f"history_{message_index}", flow_data)
            if message.get("source_refs"):
                with st.expander("Source"):
                    st.write("\n".join(message["source_refs"]))
        user_message = st.chat_input("Ask about your career… | اسأل عن مسارك المهني…")
    if not user_message: return
    st.session_state.history.append({"role":"user", "content":user_message})
    language = detect_language(user_message)
    st.session_state.agent_language = language
    if is_job_search_intent(user_message):
        if flow_data:
            agent = st.session_state.tap_agent
            if agent.get("current_state") not in {"profile_loaded", "clarification_needed"}:
                old_job_id = agent.get("selected_job_id")
                if old_job_id:
                    clear_job_widget_state(str(old_job_id))
                    agent = reset_job_dependent_state(agent, "__new_search__", None)
                    agent["selected_job_id"] = None
                agent["current_state"] = flow_data["session_state"]["initial_state"]
                agent["current_stage"] = "profile"
                st.session_state.tap_agent = agent
            st.session_state.tap_agent = transition_agent_state(
                st.session_state.tap_agent,
                "job_search_intent_detected",
                {"normalized_job_query": user_message.strip()},
                flow_data,
            )
        try:
            matches = job_index(JOBS_PATH.stat().st_mtime_ns).search(user_message, st.session_state.demo_profile)
        except (OSError, ValueError) as exc:
            answer = f"تعذر فتح فرص العمل المحلية: {exc}" if language in {"ar", "mixed"} else f"Could not load local jobs: {exc}"
            if flow_data:
                st.session_state.tap_agent = transition_agent_state(st.session_state.tap_agent, "required_runtime_data_failed", {"validated_loader_error_exists": True}, flow_data)
            st.session_state.history.append({"role":"assistant", "content":answer}); save(); st.rerun()
        if matches:
            answer = "لقيتلك فرص قريبة من طلبك:" if language in {"ar", "mixed"} else "I found opportunities matching your request:"
            event = {"role":"assistant", "content":answer, "jobs":matches, "job_language":language}
            st.session_state.history.append(event)
            if flow_data:
                agent = dict(st.session_state.tap_agent)
                agent["current_job_results"] = matches
                agent["selected_job_id"] = None
                agent["selected_job_match"] = None
                st.session_state.tap_agent = transition_agent_state(agent, "job_search_completed", {"job_results_count": len(matches)}, flow_data)
            save(); st.rerun()
        answer = "ما لقيت تطابقًا كافيًا. جرّب إزالة الموقع، اختيار Remote، أو استخدام مسمى أوسع." if language in {"ar", "mixed"} else "No close match found. Try removing the location, choosing Remote, or using a broader role title."
        if flow_data:
            agent = dict(st.session_state.tap_agent)
            agent["current_job_results"] = []
            st.session_state.tap_agent = transition_agent_state(agent, "job_search_completed", {"job_results_count": 0}, flow_data)
        st.session_state.history.append({"role":"assistant", "content":answer}); save(); st.rerun()
    if is_underspecified_job_request(user_message):
        answer = (
            "شو الدور المستهدف ومستوى خبرتك؟ مثال: Junior Backend Developer | مبتدئ."
            if language in {"ar", "mixed"}
            else "What target role and experience level should I use? Example: Junior Backend Developer | entry level."
        )
        st.session_state.history.append({"role":"assistant", "content":answer})
        if flow_data and st.session_state.tap_agent.get("current_state") in {"profile_loaded", "clarification_needed"}:
            agent = transition_agent_state(st.session_state.tap_agent, "job_search_intent_detected", {"normalized_job_query": user_message.strip()}, flow_data)
            st.session_state.tap_agent = transition_agent_state(agent, "job_search_completed", {"job_results_count": 0}, flow_data)
        save(); st.rerun()
    typed_option = find_typed_assessment_option(user_message, assessments) if assessments else None
    if typed_option:
        answer = (
            f"هذه إجابة من اختبار {typed_option['skill']}. حتى تنحسب نتيجتك، افتح بطاقة الوظيفة ثم «اختبر مهاراتي»، اختر الإجابة داخل النموذج، واضغط «أرسل الإجابات». لن أصحح إجابات الاختبار داخل الشات قبل الإرسال."
            if language in {"ar", "mixed"}
            else f"This looks like an answer from the {typed_option['skill']} assessment. To record your score, open the job card, choose it inside “Test My Skills,” and submit the form. Assessment answers are not graded in chat before submission."
        )
        st.session_state.history.append({"role":"assistant", "content":answer})
        save(); st.rerun()
    if is_roadmap_ui_request(user_message):
        answer = (
            "لفتح الخطة: ابحث أولًا عن وظيفة محددة، ثم افتح «خطة قصيرة لسد فجوة المهارات» تحت بطاقة الوظيفة. الخطة تُبنى من المهارات المطلوبة الناقصة لتلك الوظيفة، لذلك لا تظهر كإجابة عامة منفصلة."
            if language in {"ar", "mixed"}
            else "To open the roadmap, search for a specific job first, then expand “Mini Skill-Gap Roadmap” beneath its card. The roadmap is built from that job’s missing required skills."
        )
        st.session_state.history.append({"role":"assistant", "content":answer})
        save(); st.rerun()
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
        save(); st.rerun()
    special = boundary_response(user_message)
    retrieved = retriever.search(user_message, threshold=FAST_MATCH_THRESHOLD)
    if special: answer = special
    elif retrieved:
        # Known TAP topics return instantly without embeddings or Ollama generation.
        answer = instant_answer(retrieved[0], language, st.session_state.profile, user_message)
    else:
        answer = fast_clarification(user_message, st.session_state.profile)
    event = {"role":"assistant", "content":answer}
    if any(r["item"]["category"].startswith("tap") or r["item"]["intent"].startswith("tap_") for r in retrieved):
        refs = [ref for r in retrieved for ref in r["item"].get("source_refs", [])]
        if refs:
            event["source_refs"] = refs
    st.session_state.history.append(event)
    if flow_data and retrieved:
        st.session_state.tap_agent = transition_agent_state(
            st.session_state.tap_agent,
            "general_career_question_answered",
            {"fast_matcher_answer_was_returned": True},
            flow_data,
        )
        if st.session_state.tap_agent.get("current_state") not in {"profile_loaded", "clarification_needed", "data_unavailable"}:
            st.session_state.tap_agent_interrupted = True
    save(); st.rerun()
if __name__ == "__main__": main()
