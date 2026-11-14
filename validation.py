"""Input validation for Civic Air Quality Briefing Studio."""

from typing import Any

MAX_TABLE_CHARS = 2000

VALID_ROLES: dict[str, str] = {
    "ward_officer": "Ward Officer",
    "housing_society": "Housing Society",
    "school": "School",
}

VALID_LANGUAGES: set[str] = {"English", "Hindi"}
VALID_READING_LEVELS: set[str] = {"Simple", "Standard"}


def validate_brief_request(payload: Any) -> tuple[dict[str, str] | None, dict[str, str]]:
    """Validate incoming briefing request payload.

    Returns a tuple of (cleaned_data, field_errors). If field_errors is non-empty,
    cleaned_data is None.
    """
    if not isinstance(payload, dict):
        return None, {"form": "Request body must be a JSON object."}

    errors: dict[str, str] = {}

    raw_table = payload.get("raw_table")
    if not isinstance(raw_table, str) or not raw_table.strip():
        errors["raw_table"] = "Please paste or upload an air quality data table."
    elif len(raw_table.strip()) > MAX_TABLE_CHARS:
        errors["raw_table"] = (
            f"Data table must be {MAX_TABLE_CHARS} characters or fewer "
            f"(currently {len(raw_table.strip())})."
        )

    role = payload.get("role", "ward_officer")
    if not isinstance(role, str) or role not in VALID_ROLES:
        errors["role"] = "Please choose Ward Officer, Housing Society, or School."

    language = payload.get("language", "English")
    if not isinstance(language, str) or language not in VALID_LANGUAGES:
        errors["language"] = "Please choose English or Hindi."

    reading_level = payload.get("reading_level", "Standard")
    if not isinstance(reading_level, str) or reading_level not in VALID_READING_LEVELS:
        errors["reading_level"] = "Please choose Simple or Standard reading level."

    if errors:
        return None, errors

    return {
        "raw_table": raw_table.strip(),
        "role": role,
        "role_label": VALID_ROLES[role],
        "language": language,
        "reading_level": reading_level,
    }, {}
