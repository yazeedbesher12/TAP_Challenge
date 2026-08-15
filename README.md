# TAP Career Companion

A lightweight local Arabic-English career chatbot for Palestine and the wider MENA region. It answers from the supplied local knowledge base immediately, without Ollama or any cloud AI API.

## Features

- Arabic, English, and code-switched guidance with RTL-aware chat display.
- Profile-aware CV, LinkedIn, job-search, interview, remote-work, and TAP advice.
- Instant in-memory lexical matching across the 47 supplied knowledge items; no embedding model or vector database is loaded.
- Local-only optional profile/chat memory and one-click deletion.
- Immediate clarification for questions that are not covered by the knowledge base.

## Architecture and privacy

`message → language detection → instant local knowledge match → direct response`. Questions with no confident match receive an immediate focused clarification request.

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
pytest -q
python -m compileall app.py src
```

## Example queries

- `أنا Computer Engineering student ومحتار بين AI و Full Stack`
- `How can I improve my LinkedIn headline?`
- `عندي remote interview الأسبوع الجاي for a junior data role`

## Troubleshooting and limitations

No model needs to start before a reply, which removes the slow generation delay. The tradeoff is that unusually phrased or out-of-knowledge-base questions get a short clarification request rather than a generated answer. Advice is career coaching, not legal, tax, immigration, medical, or mental-health advice. TAP facts are limited to the supplied JSON and should be verified if they may have changed.
