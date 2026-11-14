# Civic Air Quality Briefing Studio

An AI-driven civic intelligence web app that helps local authorities, housing societies, and schools turn messy air quality tables into traceable briefings, prioritized local actions, session-over-session diffs, staff internal notes, and multilingual citizen advisories.

## Features
- **Messy table parsing & data-gap flagging (`logic.py`):** Assigns stable row IDs (`R1`, `R2`, ...), flags missing/non-numeric/out-of-range readings, detects mixed units (`ug/m3` vs `AQI`), and computes deterministic summary metrics.
- **Role-tailored briefings (`ai.py`):** Generates prioritized local actions suited to **Ward Officer**, **Housing Society**, or **School**, citing exact row IDs.
- **Traceability guard:** Drops any AI finding whose cited row IDs do not exist in the parsed input.
- **Brief-to-brief comparison:** Compares each new brief against the previous in-session brief to highlight what changed.
- **Staff internal note + multilingual citizen advisory:** Public advisories in **English** or **Hindi** at **Simple** or **Standard** reading levels with guidance for children, older adults, and sensitive groups; staff-only internal briefing note behind `/login`.

## Staff Demo Credentials
- **Username:** `staff`
- **Password:** `ward14demo`

## Google Services Used
- **Gemini API (`google-genai`):** `ai.py` (`gemini-3.5-flash` primary, `gemini-3.5-flash-lite` fallback, structured JSON `response_schema`).
- **Cloud Run:** `Procfile` (`pw-warmup` service).
- **Secret Manager:** `GEMINI_API_KEY` (`gemini-api-key-free:latest`).
- **Cloud Logging:** Structured JSON request and AI call logs in `main.py` and `ai.py`.

## Run Locally
```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
GEMINI_API_KEY="your-key" .venv/bin/flask --app main run --port 8080
```
