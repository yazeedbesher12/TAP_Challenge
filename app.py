from __future__ import annotations
import html
from typing import Any
import streamlit as st
from src.config import FAST_MATCH_THRESHOLD, KB_PATH, MEMORY_PATH
from src.data_loader import load_knowledge_base
from src.language import detect_language, text_direction
from src.memory import delete_saved_data, empty_profile, load_saved_data, save_data
from src.fast_matcher import FastMatcher, instant_answer
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
      [data-testid="stChatInput"] { border-radius:16px; border:1px solid #b9c9d8; box-shadow:0 7px 22px rgba(28,57,86,.10); }
      .stButton > button { border-radius:10px; border:1px solid #7aa8be; font-weight:600; }
      @media (max-width:640px) { .block-container { padding:1rem .8rem 5rem; } .tap-hero { padding:1.2rem; border-radius:16px; } .tap-hero h1 { font-size:1.55rem; } }
    </style>
    """, unsafe_allow_html=True)
@st.cache_resource
def services() -> tuple[dict[str, Any], FastMatcher]:
    kb = load_knowledge_base(KB_PATH)
    return kb, FastMatcher(kb)

def init_state() -> None:
    if "initialized" not in st.session_state:
        saved = load_saved_data(MEMORY_PATH)
        st.session_state.profile, st.session_state.history = saved["profile"], saved["history"]
        st.session_state.remember = False
        st.session_state.initialized = True

def save() -> None: save_data(MEMORY_PATH, st.session_state.profile, st.session_state.history, st.session_state.remember)
def render_message(role: str, content: str) -> None:
    direction = text_direction(content)
    with st.chat_message(role):
        # Escaped HTML keeps RTL message blocks safe even for untrusted input.
        st.markdown(f'<div dir="{direction}" style="text-align:{"right" if direction == "rtl" else "left"};white-space:pre-wrap">{html.escape(content)}</div>', unsafe_allow_html=True)

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
    st.markdown("""
    <section class="tap-hero">
      <h1>💼 TAP Career Companion</h1>
      <p dir="rtl">رفيقك المهني المحلي — خطوات عملية لمسارك المهني</p>
      <span class="tap-badge">Local · Private · Fast answers</span>
    </section>
    """, unsafe_allow_html=True)
    with st.sidebar:
        st.header("Profile | الملف المهني")
        st.caption("Add only what you want to personalize the advice.")
        st.session_state.remember = st.toggle("Remember me on this device", value=st.session_state.remember)
        labels = {"education_or_role":"Education or current role", "location":"Location", "experience_level":"Experience level", "target_roles":"Target roles", "main_skills":"Main skills", "important_projects":"Important projects", "english_level":"English level", "weekly_hours":"Weekly available hours", "career_goal":"Career goal"}
        for key, label in labels.items(): st.session_state.profile[key] = st.text_input(label, st.session_state.profile.get(key, ""), key=f"profile_{key}")
        st.session_state.profile["preferred_work_mode"] = st.selectbox("Preferred work mode", ["", "Local", "Remote", "Hybrid", "Any"], index=["", "Local", "Remote", "Hybrid", "Any"].index(st.session_state.profile.get("preferred_work_mode", "") if st.session_state.profile.get("preferred_work_mode", "") in ["", "Local", "Remote", "Hybrid", "Any"] else ""))
        st.divider()
        if st.button("New Chat", use_container_width=True): st.session_state.history = []; save(); st.rerun()
        if st.button("Delete Saved Data", use_container_width=True):
            delete_saved_data(MEMORY_PATH); st.session_state.profile = empty_profile(); st.session_state.history = []; st.success("Saved local profile and conversation deleted.")
    for message in st.session_state.history: render_message(message["role"], message["content"])
    user_message = st.chat_input("Ask about your career… | اسأل عن مسارك المهني…")
    if not user_message: return
    st.session_state.history.append({"role":"user", "content":user_message}); render_message("user", user_message)
    special = boundary_response(user_message)
    retrieved = retriever.search(user_message, threshold=FAST_MATCH_THRESHOLD)
    if special: answer = special
    elif retrieved:
        # Known TAP topics return instantly without embeddings or Ollama generation.
        answer = instant_answer(retrieved[0], detect_language(user_message), st.session_state.profile)
    else:
        answer = fast_clarification(user_message, st.session_state.profile)
    render_message("assistant", answer)
    st.session_state.history.append({"role":"assistant", "content":answer}); save()
    if any(r["item"]["category"].startswith("tap") or r["item"]["intent"].startswith("tap_") for r in retrieved):
        refs = [ref for r in retrieved for ref in r["item"].get("source_refs", [])]
        if refs:
            with st.expander("Source"): st.write("\n".join(refs))
if __name__ == "__main__": main()
