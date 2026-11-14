# Civic Air Quality Briefing Studio

Turn messy ward and society air quality tables into row-verified local briefings, prioritized actions, session diffs, and multilingual citizen advisories.

- **Live URL:** https://pw-warmup-498000306403.asia-south1.run.app
- **Try in 30 seconds:** Tap **Example: Morning Ward 14 Table (Messy)**, click **Generate Briefing**, then tap **Example: Afternoon Spike (Hindi + Simple)** and click **Generate Briefing** to see the session comparison and Hindi advisory. Sign in at `/login` with `staff` / `ward14demo` to unlock the staff-only Internal Briefing Note.

## The problem

**Civic Air Quality Briefing Studio**

Develop an AI-driven civic intelligence solution that enables local authorities, housing societies, and ward-level teams to turn raw air quality data into actionable local interventions. The solution must leverage Generative AI as a core component to interpret pasted or uploaded data tables, including messy ones with inconsistent formats, units, or missing readings, and summarize trends and likely hotspots in plain language. It should recommend prioritized local actions suited to who is asking, since a ward officer, a housing society, and a school can each do different things. Every finding should be traceable to the underlying data, with data gaps and unreliable readings clearly flagged. The assistant should compare each new brief with the previous one to show what changed, and generate both an internal briefing note and a citizen advisory in multiple languages, written for different reading levels, with extra care for children, older adults, and people sensitive to poor air.

Priya Nair, Ward 14 Civic Coordinator, reviews 18 messy sensor and manual AQI readings every morning before 9 AM. She spends an hour sorting mixed units and broken sensors before she can brief her team or warn schools and residents.

## What it does

1. **Input:** User selects their role (`Ward Officer`, `Housing Society`, or `School`), advisory language (`English` / `Hindi`), and reading level (`Simple` / `Standard`), then pastes, uploads (`.csv`/`.tsv`/`.txt`), or taps an Example chip (`templates/index.html`, `sample_data.json`).
2. **Process:** `logic.py` parses rows into `R1..Rn`, flags missing/out-of-range/mixed-unit readings, and computes numeric deltas; `ai.py` calls Gemini with structured JSON output.
3. **Result:** User gets a single-line headline verdict, row-cited hotspots and data gaps, role-tailored actions, a "What changed" diff, a staff-only internal note (`/login`), and a copyable multilingual citizen advisory.

## How it works

`User table -> validation.py -> logic.py (rows, flags, metrics) -> ai.py (Gemini JSON + cache) -> logic.validate_citations -> UI`

- **The AI decides, the code computes:** `logic.py` assigns `R1..Rn` IDs, detects missing/negative/`>999` values and mixed units, computes min/max/mean and numeric deltas, and drops any AI finding whose `cited_rows` are not in the input. Gemini handles messy schema interpretation, hotspot synthesis, role prioritization, diff narrative, and language/reading-level adaptation.
- **Fallback chain:** `gemini-3.5-flash` (20s timeout) -> single retry on `gemini-3.5-flash-lite` -> honest error (`"The analysis couldn't run right now. Please try again in a minute."`) with Retry button. Identical requests hit a 15-minute in-memory LRU cache (`ai.py`).

## Google services used

| Service | Purpose | Evidence file |
| --- | --- | --- |
| Gemini API (`google-genai`) | Structured briefing, actions, diff, multilingual advisory | `ai.py` |
| Cloud Run | Container hosting (`pw-warmup`, `asia-south1`) | `Procfile` |
| Secret Manager | Stores `GEMINI_API_KEY` (`gemini-api-key-free:latest`) | `ai.py` |
| Cloud Logging | Structured JSON request and AI latency/cache logs | `main.py`, `ai.py` |

## Evaluation notes

| Scored area | What was done | Evidence file |
| --- | --- | --- |
| Code quality | Small typed modules, docstrings, pure `logic.py`, no dead code | `main.py`, `logic.py`, `ai.py`, `validation.py` |
| Problem alignment | Messy tables, row citations, gap flags, role actions, brief diff, staff note, EN/HI advisories | `templates/index.html`, `ai.py`, `logic.py` |
| Security | CSP (`script-src 'self'`), `nosniff`, `DENY`, `textContent` only, 64 KB cap, 20 req/min/IP, hashed staff login | `main.py`, `static/app.js`, `validation.py` |
| Efficiency | 15-min LRU cache, 20s timeout, single Gemini call per action, zero build step | `ai.py`, `static/styles.css` |
| Testing | 7 `pytest` tests covering validation, parsing, headers, citations, login, rate limit, errors (Gemini mocked) | `tests/test_app.py` |
| Accessibility | WCAG 2.2 AA landmarks, skip link, `aria-live="polite"`, `aria-invalid`, `aria-describedby`, 44px targets | `templates/index.html`, `static/styles.css` |
| Documentation | Brief, prompt log, submission summary, and factual README | `README.md`, `BRIEF.md`, `docs/` |

## Run locally, tests, deploy

```bash
# Tests (Gemini mocked)
.venv/bin/pytest

# Run locally
GEMINI_API_KEY="$(gcloud secrets versions access latest --secret=gemini-api-key-free --project pw-bhopal-1114)" .venv/bin/flask --app main run --port 8080

# Deploy to Cloud Run
gcloud run deploy pw-warmup --source . --project pw-bhopal-1114 --region asia-south1 --allow-unauthenticated --max-instances 2 --set-secrets GEMINI_API_KEY=gemini-api-key-free:latest --set-env-vars GEMINI_MODEL=gemini-3.5-flash,GEMINI_FALLBACK_MODEL=gemini-3.5-flash-lite
```

## Honest limits

- Session comparison (`_previous_brief`) is stored in-memory per instance (resets on cold start or scale-out; no database per brief).
- Advisories support English and Hindi (`Simple` / `Standard` reading levels); additional languages are not included in this warm-up scope.

## How it was built

Built using Antigravity Planning Mode with structured build skills; prompt and iteration log in `docs/prompts.md`.
