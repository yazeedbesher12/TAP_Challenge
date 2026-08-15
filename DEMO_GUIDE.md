# TAP Career Companion — Five-Minute Demo Guide

## Run the final demo

From PowerShell:

```powershell
cd D:\Desktop\TAP
.\.venv\Scripts\Activate.ps1
.\run.ps1
```

Direct alternative:

```powershell
cd D:\Desktop\TAP
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open `http://localhost:8501`. No Ollama, model server, database, login, or internet service is required. “Remember me” starts disabled.

## Five-minute order

### 0:00–0:30 — Explain the project

TAP is a bilingual, local career companion. It matches a fictional demo profile to supplied demo jobs, identifies job-specific skill gaps, recommends a short roadmap, verifies selected skills, and calculates readiness using static validated JSON rules.

### 0:30–1:20 — Start the Arabic flow

Send exactly:

```text
بدي وظيفة Python Backend Developer مناسبة لمهاراتي
```

Expected first result: **Junior Backend Developer**. Point out the Arabic RTL card, match label, profile-to-job match shown in Final Readiness, matched skills, missing required skills, and the supplied job link. The link opens only after a click.

### 1:20–2:10 — Open the roadmap

Click **خطة قصيرة لسد فجوة المهارات**. Confirm that no more than two required-skill roadmaps appear. Show the learning time, source link, Learn/Build/Evaluate/Portfolio steps, evidence, and completion criteria.

### 2:10–3:20 — Verify a skill

Click **اختبر مهاراتي**. Use the **FastAPI** form for the shortest path. Before submission, point out that no answer or explanation is exposed. Answer all three questions correctly and click **أرسل الإجابات**. Expect 3/3, 100%, the passing label, corrections/explanations, and the preliminary-assessment disclaimer.

### 3:20–4:20 — Explain readiness

Open **الجاهزية النهائية للوظيفة**. Point out:

- `60% مطابقة الوظيفة + 40% اختبار المهارات` from the JSON rules.
- Strengths and priority gaps, limited to three each.
- Numerical readiness remains visible.
- The three-missing-skills gate lowers this current Backend result to **يحتاج إلى تجهيز**, even after a passed assessment.
- The roadmap action and job link remain available.
- The result is guidance, never a hiring guarantee.

The manual checklist lists Ready/Almost as acceptable for this starting message, but the current read-only profile/job data has three Backend gaps (`FastAPI`, `PostgreSQL`, `Docker`). The validated readiness rule therefore correctly caps it at Needs Preparation. Do not alter the data for the presentation.

### 4:20–5:00 — Show the safety/fallback and close

Start a New Chat and send:

```text
بدي شغل
```

Expected: one focused request for the target role and experience level, with no invented job, assessment, or readiness card.

Close with:

> TAP لا يعرض الوظيفة فقط؛ بل يوضح مدى مناسبتها، يكشف الفجوة، يقترح طريقاً عملياً، ويتحقق من الجاهزية قبل التقديم.

## Backup scenario: failed required skill

Send:

```text
اعرضلي وظيفة Backend Developer بتطلب Docker
```

Open **اختبر مهاراتي**, use the Docker form, and answer exactly one question correctly. Submit once. Expected:

- 1/3 and 33%.
- **تحتاج إلى تدريب إضافي**.
- Correct answers and explanations appear only after submission.
- Final readiness is never Ready to Apply.
- The failed-required-skill explanation and roadmap action remain visible.

## English backup

Send:

```text
Show me a Python developer job that matches my skills
```

Expected: English LTR job cards, roadmap, three-question assessment, readiness formula, action, and disclaimer. The same JSON weights and gates apply in both languages.

## Known limitations

- Jobs and application URLs are fictional demo records; `.example` links demonstrate click behavior and may not resolve to a public vacancy.
- Matching is lexical and deterministic, so unusually phrased requests may need clarification.
- The Backend demo profile has three real required gaps, so its final status is capped by design.
- Assessments are preliminary three-question demo checks, not professional certification.
- Assessment/readiness state lasts only for the current Streamlit session.
- `data/demo_scenarios.json` is a manual checklist, not runtime knowledge.

## Recovery

If Streamlit must be restarted:

1. Stop it with `Ctrl+C` in the PowerShell window.
2. Run `cd D:\Desktop\TAP`.
3. Run `.\run.ps1`.
4. Refresh `http://localhost:8501`.
5. Restart from the exact Arabic message above. Session-only assessment results intentionally reset after a server restart.

If port 8501 is occupied:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
```

## Pre-QA JSON integrity baseline (SHA-256)

| File | SHA-256 |
|---|---|
| `tap_career_companion_qa.json` | `D64C0BA06077B29D79C8CA13750D2D6245B96275D79D2298A6A5BF2803FCF645` |
| `data/demo_scenarios.json` | `C4D558F2CC9AC13A11AC7698926F9A2B78B89CAA4A55D8220CE79E5C7DEF33CD` |
| `data/demo_user_profile.json` | `C8C05061675037B22F3D18270C03A77853E5ECA2BD28210DC0144E43B0C5DF1E` |
| `data/jobs.json` | `456923840EABC003C853DF3A826359C627766B55196E229939E9BC2726A7AE48` |
| `data/learning_resources.json` | `46CAE5C7F6D3725D08BE9FD263AA74660D72C6447AEF6415DCCB5F2C6F8F13FB` |
| `data/readiness_rules.json` | `77B6D8A345A75EEC229E37B360A27B4FFFEBFD75A8FB011D8E4306DB6F318502` |
| `data/skill_assessment_questions.json` | `B11F2A14BA826F5A9E945779B17B885A3E65DA3963D5F5F91A7A687F2286209D` |
