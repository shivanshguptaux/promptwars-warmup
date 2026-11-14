"""Pytest suite for Civic Air Quality Briefing Studio (Gemini mocked)."""

import json
from unittest.mock import MagicMock, patch

import pytest

import ai
import logic
import main
import validation


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    """Reset in-memory state and rate limiter between tests."""
    main._previous_brief = None
    main._ip_requests.clear()
    ai._cache.clear()
    monkeypatch.setenv("GEMINI_API_KEY", "test-mock-key")


def _sample_ai_json() -> str:
    return json.dumps(
        {
            "headline_verdict": "Elevated Alert: Peak at School Gate — Move assembly indoors.",
            "trends_and_hotspots": [
                {"finding": "School Gate North recorded 168 ug/m3.", "cited_rows": ["R1"], "severity": "high"},
                {"finding": "Hallucinated row check.", "cited_rows": ["R999"], "severity": "low"},
            ],
            "data_gaps_summary": [
                {"issue": "Industrial Naka sensor reported negative value.", "cited_rows": ["R2"]}
            ],
            "prioritized_actions": [
                {
                    "priority": 1,
                    "action": "Move morning assembly indoors.",
                    "reason": "High PM2.5 at gate.",
                    "cited_rows": ["R1"],
                }
            ],
            "what_changed": "First brief in session.",
            "internal_briefing_note": "Dispatch technician to R2.",
            "citizen_advisory": {
                "language": "English",
                "reading_level": "Simple",
                "title": "Air Quality Advisory",
                "general_guidance": "Keep windows closed near traffic.",
                "vulnerable_groups": {
                    "children": "Play indoors today.",
                    "older_adults": "Skip morning walks.",
                    "sensitive_people": "Keep inhaler nearby.",
                },
            },
        }
    )


def test_validation_rejects_empty_and_overlong():
    cleaned, errors = validation.validate_brief_request({"raw_table": "   ", "role": "school"})
    assert cleaned is None
    assert "raw_table" in errors

    cleaned, errors = validation.validate_brief_request({"raw_table": "x" * 2001, "role": "school"})
    assert cleaned is None
    assert "raw_table" in errors


def test_logic_parses_messy_table_and_flags_gaps():
    table = (
        "Station,PM2.5,AQI,Unit\n"
        "School Gate,168,,ug/m3\n"
        "Industrial Naka,-12,,ug/m3\n"
        "Greenwoods,MISSING,,ug/m3\n"
        "Market Chowk,,312,AQI\n"
    )
    parsed = logic.parse_and_analyze_table(table)
    assert parsed["metrics"]["total_rows"] == 4
    assert parsed["metrics"]["valid_count"] == 2
    assert parsed["metrics"]["flagged_count"] == 2
    assert parsed["metrics"]["mixed_units"] is True
    assert [f["row_id"] for f in parsed["flagged_rows"]] == ["R2", "R3"]


def test_health_and_security_headers():
    client = main.app.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "script-src 'self'" in resp.headers["Content-Security-Policy"]


def test_analyze_success_drops_invalid_citations_and_gates_staff_note():
    mock_resp = MagicMock()
    mock_resp.text = _sample_ai_json()
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    with patch("ai.genai.Client", return_value=mock_client):
        client = main.app.test_client()
        resp = client.post(
            "/analyze",
            json={
                "role": "school",
                "language": "English",
                "reading_level": "Simple",
                "raw_table": "Station,PM2.5,Unit\nSchool Gate,168,ug/m3\nIndustrial Naka,-12,ug/m3",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        # R999 finding dropped
        assert len(data["trends_and_hotspots"]) == 1
        assert data["trends_and_hotspots"][0]["cited_rows"] == ["R1"]
        # Staff note hidden when not signed in
        assert data["is_staff"] is False
        assert data["internal_briefing_note"] is None


def test_staff_login_unlocks_internal_note():
    mock_resp = MagicMock()
    mock_resp.text = _sample_ai_json()
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    client = main.app.test_client()
    login_resp = client.post("/login", data={"username": "staff", "password": "ward14demo"})
    assert login_resp.status_code == 302

    with patch("ai.genai.Client", return_value=mock_client):
        resp = client.post(
            "/analyze",
            json={
                "role": "ward_officer",
                "language": "English",
                "reading_level": "Standard",
                "raw_table": "Station,PM2.5,Unit\nSchool Gate,168,ug/m3\nIndustrial Naka,-12,ug/m3",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["is_staff"] is True
        assert data["internal_briefing_note"] == "Dispatch technician to R2."


def test_analyze_fallback_and_honest_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = main.app.test_client()
    resp = client.post(
        "/analyze",
        json={
            "role": "ward_officer",
            "language": "English",
            "reading_level": "Standard",
            "raw_table": "Station,PM2.5,Unit\nGate,120,ug/m3",
        },
    )
    assert resp.status_code == 503
    assert "try again in a minute" in resp.get_json()["error"].lower()


def test_rate_limit_enforced():
    client = main.app.test_client()
    for _ in range(20):
        main._is_rate_limited("10.0.0.1")
    resp = client.post(
        "/analyze",
        headers={"X-Forwarded-For": "10.0.0.1"},
        json={"role": "school", "language": "English", "reading_level": "Simple", "raw_table": "a,1"},
    )
    assert resp.status_code == 429
