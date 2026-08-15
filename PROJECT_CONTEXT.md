# Project Context: TAP Career Companion

## Purpose and challenge fit

This is a local bilingual career companion for Palestinian and wider MENA job seekers. It provides multilingual, privacy-first, immediate TAP knowledge-base guidance without requiring a language model at runtime.

## Architecture and decisions

The runtime path is: language detection → in-memory lexical matching over question variants → direct bilingual answer and action steps from the JSON. It does not load embeddings, build vectors, call Ollama, or depend on a GPU. This makes routine career questions immediate on the target hardware. An unmatched question receives a focused local clarification request. A vector database and fine-tuning are unnecessary for 47 items.

`tap_career_companion_qa.json` is required and untouched. It contains metadata, assistant policy, and items with IDs, category, intent, variants, bilingual core answers, actions, tags, and sometimes sources. Startup validates this schema. The application uses its question variants and tags for instant local matching; there is no embedding cache.

## Privacy, states, and constraints

Everything stays local. Streamlit telemetry is disabled. Optional memory lives only in `data/personal_memory.json`, excludes secrets by design, tolerates corruption, and deletion only removes that file. Principal UI states are normal chat and optional remembered memory.

Target hardware is Windows 11, i5 10th gen, 16 GB RAM, GTX 1650 4 GB. Known limitations: lexical matching is intentionally lightweight and may ask for clarification for unusually phrased questions; factual information can become stale; free-form generative coaching and mock-interview feedback are intentionally disabled to guarantee fast replies.

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
