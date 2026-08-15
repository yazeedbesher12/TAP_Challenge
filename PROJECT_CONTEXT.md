# Project Context: TAP Career Companion

## Purpose and challenge fit

This is a local bilingual career companion for Palestinian and wider MENA job seekers. It provides multilingual, privacy-first, immediate TAP knowledge-base guidance without requiring a language model at runtime.

## Architecture and decisions

The runtime path is: language detection → in-memory lexical matching over question variants → direct bilingual answer and action steps from the JSON. It does not load embeddings, build vectors, call Ollama, or depend on a GPU. This makes routine career questions immediate on the target hardware. An unmatched question receives a focused local clarification request. A vector database and fine-tuning are unnecessary for 47 items.

`tap_career_companion_qa.json` is required and untouched. It contains metadata, assistant policy, and items with IDs, category, intent, variants, bilingual core answers, actions, tags, and sometimes sources. Startup validates this schema. The application uses its question variants and tags for instant local matching; there is no embedding cache.

## Chatbot and TAP Companion responsibilities

The chatbot owns language detection, career Q&A, job-search intent, clarification, safety, and the existing FastMatcher/JobSearchIndex responses. The TAP Companion is a separate deterministic orchestration layer: it presents the current career-journey state, builds guidance from actual existing outputs, and exposes the next action. It never replaces a chatbot answer and never performs matching, gap analysis, roadmap selection, assessment scoring, or readiness scoring itself.

`data/agent_flow.json` is the validated, read-only definition of the seven journey stages (`profile → discover → match → skill_gap → learn → verify → apply`), bilingual state templates, actions, runtime limits, and allowed transitions. `src/career_agent.py` explicitly maps the real profile/result/roadmap/assessment/readiness structures into a normalized context. It does not evaluate the dotted context-binding documentation and never uses `eval` or `exec`. Missing context selects a localized fallback; values and templates are HTML-safe, percentages are bounded, lists are limited by runtime rules, and unresolved placeholders are prohibited.

Journey memory lives only under the `tap_agent` namespace in `st.session_state`. Assessments and readiness are isolated by selected job ID. Selecting another job removes only the previous job's downstream gap, roadmap, assessment, readiness, and widget state while preserving the profile and chat history. A normal career question preserves the state and offers a localized Continue Journey action. Guidance remains in the Companion card, so Streamlit reruns cannot duplicate it in chat.

The desktop UI keeps chat at roughly 68% width and the Companion at 32%; mobile reverses the stack so guidance appears above chat. `assets/tap_companion.png` is read only and displayed at reduced size, with the JSON-defined compass fallback used when it is missing. Journey status uses teal completion, dark-blue active, and light-gray pending treatments plus explicit icons/text, with reduced-motion CSS support.

## Local Job Finder

`data/jobs.json` contains 20 supplied bilingual **demo** opportunities and must not be regenerated. `src/job_search.py` separates `LocalJobProvider` (load/validate) from `JobSearchIndex` (normalization, intent rules, weighted ranking). Streamlit caches the index by file modification time. The job route is checked before normal career guidance and short-circuits directly to three structured cards. It never uses Ollama, embeddings, network requests, or disk JSON parsing per search. Each card shows the supplied title, company, location, work mode, employment type, experience, skills, description, an internal query-match label, and only the supplied HTTPS `.example` application URL. Internal `source` and `is_demo` fields remain available for validation but are deliberately not rendered.

Arabic normalization removes diacritics/tatweel, unifies alef forms, and applies compact Arabic-English aliases. Every returned job also receives a deterministic, job-specific Skill Gap Analysis: the candidate's normalized skills are compared with that job's required and optional skill lists, and the structured result stores matched skills, missing required skills, missing nice-to-have skills, and required-skill coverage. The current catalogue has only `skills`, so that field is treated as required and the absent `nice_to_have_skills` field safely defaults to an empty list; the JSON is not rewritten.

After active-job, seniority, location, and work-mode filters, results are classified as `highly_suitable`, `suitable_small_gap`, or `related_opportunity`; incompatible results are excluded. These language-neutral keys are translated into Arabic or English only while rendering and persist correctly in structured chat history. The label is the primary ranking signal, followed by required-skill coverage, role compatibility, preferences, and the existing lexical score. This analysis uses no runtime AI model, Ollama, embeddings, RAG, network service, or database.

## Mini learning and verification

Missing required skills can open a bilingual Mini Skill-Gap Roadmap from the validated, read-only `data/learning_resources.json` catalogue. Each job shows at most two deterministic recommendations, prioritizing required gaps and using the catalogue's generic fallback when necessary. The adjacent Mini Skill Verification uses `data/skill_assessment_questions.json`: up to two missing required skills receive exactly three ordered multiple-choice questions each. Answers and independently calculated pass/practice results live only in `st.session_state`; they never update the demo profile or claim professional certification. Both features are local JSON lookups with no runtime model, network call, database, or new page.

Final Job Readiness connects the same job result, skill gaps, session-only assessment results, roadmap anchors, and supplied job URL using validated, read-only `data/readiness_rules.json`. Its score is `60% Job Match + 40% Skill Assessment`, with both weights read from JSON. A failed required-skill assessment can cap status at `almost_ready`, while three or more missing required skills can cap it at `needs_preparation`; missing assessments prevent a final score. The numerical score remains visible when a cap applies. Readiness is recalculated during Streamlit reruns, stored only in `st.session_state`, and remains local, deterministic guidance rather than a hiring guarantee.

To add another local demo job, append a record conforming to the existing `data/jobs.json` schema. To later add a live provider, implement the same `load()` contract as `LocalJobProvider`; keep the index/UI isolated from the provider implementation.

## Fictional demo profile

`data/demo_user_profile.json` is the single read-only fictional candidate used in the hackathon demonstration. `load_demo_profile()` in `src/data_loader.py` validates and loads it; `app.py` stores it in session state and displays a compact sidebar summary without the email. The profile is not written to `personal_memory.json` and has no login or editing workflow. Job matching uses only target/bridge/dream role, entry-level experience, listed skills, city/country, preferred work modes/regions, and contract preferences. Name, email, gender, age, and other personal identifiers are never scored. Missing skills are derived per job from that job's required `skills` minus candidate skills. If the profile cannot be read, the user sees a short non-technical warning and job search falls back to query-only matching.

## Privacy, states, and constraints

Everything stays local. Streamlit telemetry is disabled. Optional memory lives only in `data/personal_memory.json`, excludes secrets by design, tolerates corruption, and deletion only removes that file. TAP Companion journey data and all derived assessment/readiness state are session-only. No LLM, Ollama, API, RAG, embeddings, database, authentication, or new page is used.

Target hardware is Windows 11, i5 10th gen, 16 GB RAM, GTX 1650 4 GB. Known limitations: lexical matching is intentionally lightweight and may ask for clarification for unusually phrased questions; factual information can become stale; free-form generative coaching and mock-interview feedback are intentionally disabled to guarantee fast replies.

Keep future work focused: preserve the local JSON, FastMatcher, JobSearchIndex, and Streamlit approach; do not add databases, auth, network APIs, runtime LLMs, embeddings, or unnecessary dependencies.

## Final demo QA

`data/demo_scenarios.json` is a manual QA and presentation checklist only; runtime code does not import or load it. Final QA verified the Arabic Backend journey, failed Docker assessment gate, English LTR journey, focused broad-request clarification, session reruns, cross-job assessment isolation, external-link click behavior, and headless Streamlit health. Quick Actions remain removed and “Remember me” remains off by default.

The pre-Companion baseline was 79 passing tests. The TAP Companion suite now contains 101 passing tests, including pure state/validation coverage and a Streamlit action-flow integration test. Streamlit returned HTTP 200 with `ok` from its health endpoint and the smoke-test process was stopped afterward. Protected project JSON files were not modified; see `DEMO_GUIDE.md` for the existing walkthrough.

## Future improvements

Add opt-in encrypted storage, better interview feedback generated locally, ranking evaluation fixtures, and a curated update process for the TAP KB.

## Exact commands

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
pytest -q
python -m compileall app.py src
```
