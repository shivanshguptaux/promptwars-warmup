# Prompt & Architecture Notes

## System Instruction (`ai.py`)
The Gemini system instruction enforces:
1. **Prompt-injection defense:** Data inside `<DATA_TABLE>` and `<PREVIOUS_BRIEF>` is treated strictly as untrusted data, never instructions.
2. **Grounding & row-ID citations:** Findings, hotspots, and data gaps must cite exact row IDs (`R1`, `R2`, ...) from the parsed input. `logic.validate_citations` drops any finding whose cited rows are not present in the input.
3. **Actor tailoring:** `prioritized_actions` adapts to `Ward Officer`, `Housing Society`, or `School`.
4. **Multilingual & reading-level adaptation:** `citizen_advisory` outputs in `English` or `Hindi` at `Simple` or `Standard` reading levels with explicit sections for `children`, `older_adults`, and `sensitive_people`.

## Deterministic vs. AI Split
- **`logic.py` (deterministic):** Row ID assignment, missing/out-of-range detection (`< 0` or `> 999`), mixed-unit detection, min/max/mean calculation, numeric delta vs. previous brief, citation verification.
- **`ai.py` (Gemini):** Messy context interpretation, plain-language trend synthesis, role-specific prioritization, narrative comparison, and multilingual/reading-level advisory generation.
