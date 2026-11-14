"""Flask routes, security headers, rate limiting, and JSON logging."""

import json
import logging
import os
import time
from collections import deque
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ai import AIAnalysisError, generate_briefing
from logic import compute_brief_delta, parse_and_analyze_table, validate_citations
from validation import validate_brief_request

BASE_DIR = Path(__file__).resolve().parent
SAMPLE_DATA_PATH = BASE_DIR / "sample_data.json"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024  # 64 KB
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(24)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("pw-warmup")

# Simple staff demo credentials (hashed password; demo creds shown on login page & README)
STAFF_USERNAME = "staff"
STAFF_PASSWORD_HASH = generate_password_hash("ward14demo")

# In-memory previous brief store (per-instance, no database per brief)
_previous_brief: dict[str, Any] | None = None

# Per-IP sliding window rate limiter: 20 requests per 60 seconds on AI routes
_RATE_LIMIT_MAX = 20
_RATE_LIMIT_WINDOW_S = 60.0
_ip_requests: dict[str, deque[float]] = {}


def _load_examples() -> list[dict[str, str]]:
    """Load example input datasets from sample_data.json."""
    try:
        data = json.loads(SAMPLE_DATA_PATH.read_text(encoding="utf-8"))
        return data.get("examples", [])
    except (OSError, json.JSONDecodeError):
        return []


def _client_ip() -> str:
    """Return client IP respecting Cloud Run X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _is_rate_limited(ip: str) -> bool:
    """Enforce 20 requests/minute per IP."""
    now = time.monotonic()
    bucket = _ip_requests.setdefault(ip, deque())
    while bucket and (now - bucket[0]) > _RATE_LIMIT_WINDOW_S:
        bucket.popleft()
    if len(bucket) >= _RATE_LIMIT_MAX:
        return True
    bucket.append(now)
    return False


@app.after_request
def add_security_headers_and_log(response: Any) -> Any:
    """Attach security headers and emit one JSON log line per request."""
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"

    logger.info(
        json.dumps(
            {
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "ip": _client_ip(),
            }
        )
    )
    return response


@app.errorhandler(413)
def payload_too_large(_err: Any) -> tuple[Any, int]:
    """Handle request bodies exceeding MAX_CONTENT_LENGTH."""
    return jsonify({"error": "Upload or text exceeds the 64 KB limit."}), 413


@app.get("/health")
def health() -> tuple[Any, int]:
    """Cloud Run health check endpoint."""
    return jsonify({"status": "ok"}), 200


@app.get("/")
def index() -> str:
    """Render the Civic Air Quality Briefing Studio."""
    return render_template(
        "index.html",
        examples=_load_examples(),
        is_staff=bool(session.get("is_staff")),
        has_previous_brief=_previous_brief is not None,
    )


@app.route("/login", methods=["GET", "POST"])
def login() -> Any:
    """Simple staff-only sign-in to unlock the internal briefing note."""
    error: str | None = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == STAFF_USERNAME and check_password_hash(STAFF_PASSWORD_HASH, password):
            session["is_staff"] = True
            return redirect(url_for("index"))
        error = "Invalid staff username or password."
    return render_template("login.html", error=error)


@app.post("/logout")
def logout() -> Any:
    """Sign out of staff view."""
    session.pop("is_staff", None)
    return redirect(url_for("index"))


@app.post("/analyze")
def analyze() -> tuple[Any, int]:
    """Validate input, parse table, run Gemini briefing, and compare with previous brief."""
    global _previous_brief

    if _is_rate_limited(_client_ip()):
        return (
            jsonify(
                {
                    "error": "Too many requests from this IP. Please wait a minute and try again.",
                    "retryable": True,
                }
            ),
            429,
        )

    payload = request.get_json(silent=True)
    cleaned, field_errors = validate_brief_request(payload)
    if field_errors or cleaned is None:
        return jsonify({"error": "Please fix the highlighted fields.", "field_errors": field_errors}), 400

    parsed = parse_and_analyze_table(cleaned["raw_table"])
    if parsed["metrics"]["total_rows"] == 0:
        return (
            jsonify(
                {
                    "error": "Could not find any data rows in the table.",
                    "field_errors": {"raw_table": "Paste at least one data row (CSV, TSV, or spaced columns)."},
                }
            ),
            400,
        )

    delta = compute_brief_delta(parsed["metrics"], _previous_brief)

    try:
        ai_result = generate_briefing(
            parsed_data=parsed,
            role=cleaned["role"],
            role_label=cleaned["role_label"],
            language=cleaned["language"],
            reading_level=cleaned["reading_level"],
            delta=delta,
            previous_brief=_previous_brief,
        )
    except AIAnalysisError as exc:
        return jsonify({"error": str(exc), "retryable": True}), 503

    valid_ids = set(parsed["row_ids"])
    validated_ai = validate_citations(ai_result, valid_ids)

    # Gate staff-only internal briefing note unless signed in as staff
    is_staff = bool(session.get("is_staff"))
    internal_note = validated_ai.get("internal_briefing_note") if is_staff else None

    _previous_brief = {
        "role": cleaned["role"],
        "role_label": cleaned["role_label"],
        "metrics": parsed["metrics"],
        "headline_verdict": validated_ai.get("headline_verdict", ""),
    }

    return (
        jsonify(
            {
                "role_label": cleaned["role_label"],
                "metrics": parsed["metrics"],
                "flagged_rows": parsed["flagged_rows"],
                "delta": delta,
                "headline_verdict": validated_ai.get("headline_verdict", ""),
                "trends_and_hotspots": validated_ai.get("trends_and_hotspots", []),
                "data_gaps_summary": validated_ai.get("data_gaps_summary", []),
                "prioritized_actions": validated_ai.get("prioritized_actions", []),
                "what_changed": validated_ai.get("what_changed", ""),
                "internal_briefing_note": internal_note,
                "is_staff": is_staff,
                "citizen_advisory": validated_ai.get("citizen_advisory", {}),
            }
        ),
        200,
    )
