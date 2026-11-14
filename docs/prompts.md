# Prompt & Build Log

1. **Brief & Check (`/pw-brief-check`):**
   - *Prompt:* Transcribed the warm-up challenge screenshot ("Civic Air Quality Briefing Studio") into `BRIEF.md`, defined the single user (Priya Nair, Ward 14 Civic Coordinator), Desk layout, golden path, and deterministic/AI split.
   - *Outcome:* Verified zero drift from the challenge text; noted accessibility details to enforce during build.

2. **Architecture Plan (`/pw-plan`):**
   - *Prompt:* Planned file structure (`main.py`, `logic.py`, `validation.py`, `ai.py`, `templates/`, `static/`), routes (`/`, `/analyze`, `/login`, `/logout`, `/health`), Gemini `BriefingResponse` schema, and 4 build steps.
   - *Owner change:* Requested 0 real Gemini calls during build/testing to preserve quota for evaluators and the main challenge.

3. **Golden Path Build (`/pw-build`):**
   - *Prompt:* Built Flask app, deterministic messy-table parser and gap detector (`logic.py`), input validator (`validation.py`), accessible two-column Desk UI (`templates/index.html`, `static/styles.css`, `static/app.js`), staff sign-in (`templates/login.html`), and temporary stub in `ai.py`.
   - *Outcome:* Verified `/health`, `/`, and `/analyze` locally with 0 API calls.

4. **Gemini Integration (`/pw-gemini`):**
   - *Prompt:* Replaced stub in `ai.py` with `google-genai` client (`HttpOptions(timeout=20_000)`), `BriefingResponse` schema, `gemini-3.5-flash` -> `gemini-3.5-flash-lite` fallback, 15-minute LRU cache, honest error, and strict citation filtering in `logic.validate_citations`.
   - *Outcome:* Verified missing-key honest error (`503`) and mocked fallback/cache/citation-dropping.

5. **Tests, Docs & Deploy (`/pw-deploy`, `/pw-docs`):**
   - *Prompt:* Added 7 mocked `pytest` tests (`tests/test_app.py`), pushed public repo `shivanshguptaux/promptwars-warmup`, deployed `pw-warmup` to Cloud Run, verified live `/health` and `/`, and generated `README.md`, `docs/submission.md`, and `docs/prompts.md`.
