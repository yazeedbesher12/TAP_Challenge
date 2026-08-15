# TAP Career Companion

A lightweight local Arabic-English career chatbot for Palestine and the wider MENA region. It answers from the supplied local knowledge base immediately, without Ollama or any cloud AI API.

## Features

- Arabic, English, and code-switched guidance with RTL-aware chat display.
- Profile-aware CV, LinkedIn, job-search, interview, remote-work, and TAP advice.
- Instant in-memory lexical matching across the 47 supplied knowledge items; no embedding model or vector database is loaded.
- Local-only optional profile/chat memory and one-click deletion.
- Read-only fictional demo candidate profile used only to personalize local job ranking.
- Immediate clarification for questions that are not covered by the knowledge base.
- Local Job Finder over `data/jobs.json`: searches 20 bilingual demo opportunities and shows the best three application cards.
- Deterministic job-specific Skill Gap Analysis, bilingual learning roadmaps, three-question skill verification, and Final Job Readiness in the same chat flow.
- A bilingual TAP Companion that guides the real journey state from profile through discovery, matching, learning, verification, and application.

## TAP Companion

The chat remains the primary interaction area. Beside it, the TAP Companion reads the actual session profile, current job results, selected job, skill gaps, roadmaps, submitted assessments, and readiness result. Its state machine and localized templates come from the validated, read-only `data/agent_flow.json`; `src/career_agent.py` applies only a finite set of allowed transitions and never evaluates JSON expressions.

Select a job from its existing result card, then use the Companion's real actions to analyze the gap, open that job's roadmap, start the priority-skill assessment, calculate readiness, and continue toward the supplied application link. Changing jobs clears only the previous job's downstream session values. General career questions still receive the normal FastMatcher answer and do not replace or reset the journey.

The right-side card uses `assets/tap_companion.png` at a compact display size and falls back to the flow's compass visual if that asset is unavailable. The layout stacks the Companion above chat on narrow screens, supports Arabic RTL and English LTR, uses text/icons as well as color for journey status, and respects reduced-motion preferences. No model, API, database, or network call powers this feature.

## Architecture and privacy

`message → language detection → instant local knowledge match → direct response`. Questions with no confident match receive an immediate focused clarification request.

Job-search requests take a separate fast route: `intent rules → cached local job index → deterministic ranking → top 3 job cards`. Each card shows **Highly suitable**, **Suitable with a small gap**, or **Related opportunity**, followed by matched/missing skills. Missing skills connect to static roadmaps and assessments; readiness uses the JSON-defined `60% Job Match + 40% Skill Assessment` formula and gates. Type a request directly in chat, such as `بدي وظيفة Python Backend Developer مناسبة لمهاراتي` or `Show me a Python developer job that matches my skills`. No Quick Actions are used.

The fast matcher is loaded directly from the supplied JSON, so there is no embedding-model startup or cache delay. Streamlit telemetry is disabled in `.streamlit/config.toml`. The app sends no profile, CV, message, or analytics data to cloud services. “Remember me” is off by default.

## Windows installation and run

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

streamlit run app.py
# or: .\run.ps1
```

Ollama is not required for this fast mode. Hardware target: Windows 11, i5 10th generation, 16 GB RAM, GTX 1650 4 GB VRAM.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall app.py src tests
```

## Example queries

- `أنا Computer Engineering student ومحتار بين AI و Full Stack`
- `How can I improve my LinkedIn headline?`
- `عندي remote interview الأسبوع الجاي for a junior data role`
- `اعرضلي وظيفة Backend Developer بتطلب Docker`

## Troubleshooting and limitations

No model needs to start before a reply, which removes the slow generation delay. The tradeoff is that unusually phrased or out-of-knowledge-base questions get a short clarification request rather than a generated answer. Advice is career coaching, not legal, tax, immigration, medical, or mental-health advice. TAP facts are limited to the supplied JSON and should be verified if they may have changed.

The jobs are local demo data only. Every Apply button uses the supplied `.example` URL; the app never claims a real vacancy or modifies those links. Demo/internal fields such as `source` and `is_demo` remain validated in `data/jobs.json` but are never shown in job cards or chat history. To add a job, append one valid record to `data/jobs.json` using the existing schema. A future live provider can replace `LocalJobProvider` in `src/job_search.py` without changing ranking or UI code.

`data/demo_user_profile.json` is a fictional hackathon profile, loaded read-only at startup. It is shown as a compact sidebar summary without its email. Only target role, experience, skills, city/country, and work preferences affect local job ranking; identity fields never do. If it is unavailable, search still works from the typed request alone.

All supplied JSON catalogues, including `data/agent_flow.json`, are demo data loaded read-only. `data/demo_scenarios.json` is a manual QA/presentation checklist only and is never loaded by the runtime chat path. See `DEMO_GUIDE.md` for the verified five-minute walkthrough.
