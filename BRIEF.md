# Brief

Warm-up brief for **Civic Air Quality Briefing Studio**.

## Challenge (copied word for word)
**Civic Air Quality Briefing Studio**

Develop an AI-driven civic intelligence solution that enables local authorities, housing societies, and ward-level teams to turn raw air quality data into actionable local interventions. The solution must leverage Generative AI as a core component to interpret pasted or uploaded data tables, including messy ones with inconsistent formats, units, or missing readings, and summarize trends and likely hotspots in plain language. It should recommend prioritized local actions suited to who is asking, since a ward officer, a housing society, and a school can each do different things. Every finding should be traceable to the underlying data, with data gaps and unreliable readings clearly flagged. The assistant should compare each new brief with the previous one to show what changed, and generate both an internal briefing note and a citizen advisory in multiple languages, written for different reading levels, with extra care for children, older adults, and people sensitive to poor air.

## The one user
Priya Nair, Ward 14 Civic Coordinator, reviewing 18 messy sensor and manual AQI readings every morning before 9 AM to brief her ward team and warn 4,000 residents.

## Device
Desk (two-column workspace at 1024 px+ for pasting/uploading tables on the left and reading the brief/advisory on the right, collapsing to a single column on phones under 768 px).

## Their pain, in their words
"I get CSVs and WhatsApp-pasted tables with mixed units, missing hours, and broken sensors—I spend an hour guessing what's real before I can tell schools or residents what to do today."

## The golden path (what the demo shows)
1. User picks their role (Ward Officer, Housing Society, or School), chooses advisory language (English / Hindi) and reading level (Simple / Standard), and pastes or uploads a messy air quality table (or taps one of 2 Example chips).
2. Deterministic code parses rows, flags missing/out-of-range/mixed-unit readings, and compares numeric metrics against the previous brief; Gemini (single structured call) interprets trends, identifies hotspots citing exact row IDs, recommends prioritized role-specific actions, summarizes what changed since the last brief, and drafts both an internal briefing note and a citizen advisory with protections for children, older adults, and sensitive groups.
3. User gets a single-line headline verdict, traceable findings with flagged data gaps, prioritized actions for their role, a "What changed" diff, a staff-only internal briefing note, and a copyable multilingual citizen advisory.

## Screens (sketch on paper, photo attached to /pw-build)
- Screen 1: Two-column Studio — Left: role selector, language & reading-level toggles, example dataset chips, paste textarea + CSV/TSV file upload, and primary "Generate Briefing" button. Right: empty/loading state, then tabbed or stacked output (Summary & Hotspots, Prioritized Actions, What Changed, Internal Briefing Note [staff sign-in], Citizen Advisory).
- Screen 2: Simple staff sign-in modal/page (demo credentials shown on page) to unlock the internal briefing note while keeping the citizen advisory and public summary open.
- The one line the result opens with: "[Severity/Status]: [Hotspot/Trend summary] — [Top 1 immediate action for <Role>], based on [N] valid readings ([M] flagged)."

## How Gemini is used, and why AI is needed here
- Interprets messy, inconsistent table schemas/units/notes and synthesizes plain-language trends, likely hotspots, and causal context that rigid rules cannot parse.
- Generates role-tailored prioritized actions (ward officer vs housing society vs school), compares narrative shifts against the previous brief, and adapts tone/reading level across English and Hindi for vulnerable groups (children, older adults, sensitive people).

## What the code does, not the AI
- Parses pasted/uploaded CSV/TSV/text tables into numbered row IDs (`R1`, `R2`, ...) and normalizes units where deterministically possible.
- Flags missing values, negative/impossible readings, stale timestamps, and unit mismatches as explicit data gaps/unreliable rows.
- Computes min/max/mean AQI or PM2.5, counts valid vs flagged rows, stores the previous brief in memory for numeric delta comparison, and validates that every row ID cited by Gemini actually exists.

## X factor (one, from /pw-xfactor)
- Skipped for warm-up (per warm-up rules: focus on core working golden path by 11:15).

## Google services
- Gemini API: `google-genai` SDK (`ai.py`) for structured briefing, action prioritization, diff narrative, and multilingual advisory
- Cloud Run: hosting (`pw-warmup`)
- Secret Manager: `gemini-api-key-free`
- Cloud Logging: structured JSON request logs (`main.py`)

## Out of scope today
- Database persistence (in-memory previous brief only), payments, external live sensor APIs, or X factor extras.
