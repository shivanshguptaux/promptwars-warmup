"""Deterministic parsing, data-gap detection, metrics, and citation checks."""

import csv
import io
import re
from typing import Any

MISSING_TOKENS = {"", "missing", "na", "n/a", "null", "none", "-", "--", "?"}
MAX_VALID_READING = 999.0
MIN_VALID_READING = 0.0


def _detect_delimiter(lines: list[str]) -> str:
    """Detect the most likely delimiter across non-empty lines."""
    sample = "\n".join(lines[:5])
    if "\t" in sample:
        return "\t"
    if "," in sample:
        return ","
    if "|" in sample:
        return "|"
    return "whitespace"


def _split_rows(raw_table: str) -> tuple[list[str], list[list[str]]]:
    """Split raw table text into (headers, data_rows)."""
    lines = [line.strip() for line in raw_table.splitlines() if line.strip()]
    if not lines:
        return [], []

    delim = _detect_delimiter(lines)
    if delim == "whitespace":
        parsed = [re.split(r"\s{2,}", line) for line in lines]
    else:
        reader = csv.reader(io.StringIO("\n".join(lines)), delimiter=delim)
        parsed = [[cell.strip() for cell in row] for row in reader if any(c.strip() for c in row)]

    if not parsed:
        return [], []

    first_row = parsed[0]
    has_header = any(
        any(kw in cell.lower() for kw in ("station", "location", "pm2.5", "aqi", "unit", "time", "site"))
        for cell in first_row
    )
    if has_header and len(parsed) > 1:
        return first_row, parsed[1:]

    col_count = max(len(r) for r in parsed)
    headers = [f"Col{i + 1}" for i in range(col_count)]
    return headers, parsed


def _parse_numeric(value: str) -> float | None:
    """Extract a numeric value from a cell string, or return None."""
    cleaned = value.strip().lower()
    if cleaned in MISSING_TOKENS:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_and_analyze_table(raw_table: str) -> dict[str, Any]:
    """Parse messy air quality table into numbered rows, flags, and metrics."""
    headers, data_rows = _split_rows(raw_table)
    lower_headers = [h.lower() for h in headers]

    pm_idx = next((i for i, h in enumerate(lower_headers) if "pm2.5" in h or "pm25" in h), None)
    aqi_idx = next((i for i, h in enumerate(lower_headers) if "aqi" in h), None)
    unit_idx = next((i for i, h in enumerate(lower_headers) if "unit" in h), None)
    loc_idx = next(
        (i for i, h in enumerate(lower_headers) if any(k in h for k in ("station", "location", "site", "area"))),
        0,
    )

    rows: list[dict[str, Any]] = []
    valid_readings: list[float] = []
    flagged_rows: list[dict[str, str]] = []
    units_seen: set[str] = set()

    for idx, cells in enumerate(data_rows, start=1):
        row_id = f"R{idx}"
        padded = cells + [""] * max(0, len(headers) - len(cells))
        location = padded[loc_idx] if loc_idx < len(padded) and padded[loc_idx] else f"Row {idx}"

        unit_val = padded[unit_idx].strip() if unit_idx is not None and unit_idx < len(padded) else ""
        if unit_val:
            units_seen.add(unit_val.lower())

        # Determine primary numeric reading from PM2.5, AQI, or first numeric cell
        reading: float | None = None
        reading_type = "Reading"
        raw_val = ""

        if pm_idx is not None and pm_idx < len(padded) and padded[pm_idx].strip():
            raw_val = padded[pm_idx].strip()
            reading = _parse_numeric(raw_val)
            reading_type = "PM2.5"
        elif aqi_idx is not None and aqi_idx < len(padded) and padded[aqi_idx].strip():
            raw_val = padded[aqi_idx].strip()
            reading = _parse_numeric(raw_val)
            reading_type = "AQI"
        else:
            for c_idx, cell in enumerate(padded):
                if c_idx == loc_idx or c_idx == unit_idx:
                    continue
                if ":" in cell and len(cell) <= 8:
                    continue
                candidate = _parse_numeric(cell)
                if candidate is not None:
                    raw_val = cell.strip()
                    reading = candidate
                    break

        flags: list[str] = []
        if reading is None:
            flags.append(f"Missing or non-numeric reading ('{raw_val or 'empty'}')")
        elif reading < MIN_VALID_READING or reading > MAX_VALID_READING:
            flags.append(f"Unreliable out-of-range value ({reading})")
        else:
            valid_readings.append(reading)

        row_record = {
            "row_id": row_id,
            "location": location,
            "reading_type": unit_val or reading_type,
            "reading": reading,
            "raw_cells": dict(zip(headers, padded)),
            "flags": flags,
            "is_valid": len(flags) == 0,
        }
        rows.append(row_record)
        if flags:
            flagged_rows.append({"row_id": row_id, "location": location, "reason": "; ".join(flags)})

    mixed_units = len(units_seen) > 1
    valid_row_objects = [r for r in rows if r["is_valid"] and r["reading"] is not None]
    top_hotspots = sorted(valid_row_objects, key=lambda r: float(r["reading"]), reverse=True)[:3]

    metrics = {
        "total_rows": len(rows),
        "valid_count": len(valid_readings),
        "flagged_count": len(flagged_rows),
        "min_reading": round(min(valid_readings), 1) if valid_readings else None,
        "max_reading": round(max(valid_readings), 1) if valid_readings else None,
        "mean_reading": round(sum(valid_readings) / len(valid_readings), 1) if valid_readings else None,
        "mixed_units": mixed_units,
        "units_seen": sorted(units_seen),
        "top_hotspots": [
            {"row_id": r["row_id"], "location": r["location"], "reading": r["reading"], "unit": r["reading_type"]}
            for r in top_hotspots
        ],
    }

    return {
        "headers": headers,
        "rows": rows,
        "row_ids": [r["row_id"] for r in rows],
        "flagged_rows": flagged_rows,
        "metrics": metrics,
    }


def compute_brief_delta(current_metrics: dict[str, Any], previous_brief: dict[str, Any] | None) -> dict[str, Any] | None:
    """Compute deterministic numeric changes compared to the previous brief."""
    if not previous_brief or "metrics" not in previous_brief:
        return None

    prev_m = previous_brief["metrics"]
    cur_mean = current_metrics.get("mean_reading")
    prev_mean = prev_m.get("mean_reading")
    cur_max = current_metrics.get("max_reading")
    prev_max = prev_m.get("max_reading")

    mean_delta = round(cur_mean - prev_mean, 1) if cur_mean is not None and prev_mean is not None else None
    max_delta = round(cur_max - prev_max, 1) if cur_max is not None and prev_max is not None else None

    return {
        "previous_role": previous_brief.get("role_label", ""),
        "mean_delta": mean_delta,
        "max_delta": max_delta,
        "valid_count_delta": current_metrics["valid_count"] - prev_m.get("valid_count", 0),
        "flagged_count_delta": current_metrics["flagged_count"] - prev_m.get("flagged_count", 0),
    }


def validate_citations(ai_result: dict[str, Any], valid_row_ids: set[str]) -> dict[str, Any]:
    """Keep only valid row IDs and drop findings whose cited sources are not in input."""
    for section in ("trends_and_hotspots", "data_gaps_summary"):
        items = ai_result.get(section)
        if isinstance(items, list):
            kept = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                cited = item.get("cited_rows")
                if not isinstance(cited, list):
                    continue
                valid_cited = [rid for rid in cited if rid in valid_row_ids]
                if valid_cited:
                    item["cited_rows"] = valid_cited
                    kept.append(item)
            ai_result[section] = kept

    actions = ai_result.get("prioritized_actions")
    if isinstance(actions, list):
        for item in actions:
            if isinstance(item, dict) and isinstance(item.get("cited_rows"), list):
                item["cited_rows"] = [rid for rid in item["cited_rows"] if rid in valid_row_ids]
    return ai_result
