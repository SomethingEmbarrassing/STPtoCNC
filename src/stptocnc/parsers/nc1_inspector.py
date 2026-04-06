"""NC1 inspection utilities for structured, non-destructive introspection."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
from typing import Any

_FLOAT_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _maybe_float(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _parse_bo_ko_payload(payload: str) -> dict[str, Any]:
    """Parse BO/KO record payload while preserving unknown semantics."""
    tokens = payload.split()
    orientation = tokens[0] if tokens else None

    station_token = tokens[1] if len(tokens) > 1 else None
    station_value = None
    station_axis = None
    if station_token:
        m = re.match(r"([-+]?\d+(?:\.\d+)?)([a-zA-Z])?", station_token)
        if m:
            station_value = _maybe_float(m.group(1))
            station_axis = m.group(2)

    y_value = _maybe_float(tokens[2]) if len(tokens) > 2 else None
    z_or_diam_value = _maybe_float(tokens[3]) if len(tokens) > 3 else None

    return {
        "orientation": orientation,
        "station": {"value": station_value, "axis": station_axis} if station_token else None,
        "coord_2": y_value,
        "coord_3_or_diameter": z_or_diam_value,
        "raw_payload": payload,
    }


def inspect_nc1_text(text: str, source_path: str | None = None) -> dict[str, Any]:
    """Inspect NC1 text and return structured JSON-safe data.

    This inspector intentionally preserves unknown semantics under
    `unknown_records` instead of inferring machine meaning.
    """

    lines = text.splitlines()
    records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unknown_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    distinct_prefixes: set[str] = set()
    unparsed_lines = 0

    current_prefix: str | None = None

    for index, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped:
            continue

        if re.fullmatch(r"[A-Z]{1,2}", stripped):
            current_prefix = stripped
            distinct_prefixes.add(stripped)
            continue

        inline_prefix = re.match(r"^([A-Z]{2})\b\s*(.*)$", stripped)
        if inline_prefix:
            prefix = inline_prefix.group(1)
            payload = inline_prefix.group(2)
            distinct_prefixes.add(prefix)
            records[prefix].append({"line": index, "raw": raw, "payload": payload})
            current_prefix = prefix
            continue

        if current_prefix:
            records[current_prefix].append({"line": index, "raw": raw, "payload": stripped})
            continue

        unparsed_lines += 1

    # Basic extraction when present.
    part_mark = None
    for row in lines:
        s = row.strip()
        if re.fullmatch(r"[A-Za-z]{1,4}\d{2,}", s):
            part_mark = s
            break

    profile = None
    for row in lines:
        s = row.strip()
        if re.search(r"^(?:PIPE|HSS|L\d)|\bSCH\d+\b", s, flags=re.IGNORECASE):
            profile = s
            break

    material = None
    for row in lines:
        s = row.strip()
        if re.search(r"\bGR\b|\bASTM\b|A\d{2,}", s, flags=re.IGNORECASE):
            material = s
            break

    overall_length = None
    numeric_section_values: list[float] = []
    for section in ("B", "M", "L"):
        for row in records.get(section, []):
            payload = row["payload"]
            value = _maybe_float(payload)
            if value is not None:
                numeric_section_values.append(value)
    if numeric_section_values:
        overall_length = {
            "raw_value": max(numeric_section_values),
            "units": "unknown",
            "source": "max numeric from B/M/L section",
        }

    end_prep: dict[str, Any] = {}
    ak_rows = records.get("AK", [])
    if ak_rows:
        end_prep["ak_line_count"] = len(ak_rows)
        end_prep["ak_header"] = ak_rows[0]["payload"]

        col4_values: list[float] = []
        for row in ak_rows:
            nums = _FLOAT_RE.findall(row["payload"])
            if len(nums) >= 4:
                col4 = _maybe_float(nums[3])
                if col4 is not None:
                    col4_values.append(col4)
        if col4_values:
            end_prep["col4_range"] = {"min": min(col4_values), "max": max(col4_values)}

    bo_entries = [
        {"line": row["line"], **_parse_bo_ko_payload(row["payload"])}
        for row in records.get("BO", [])
    ]
    ko_entries = [
        {"line": row["line"], **_parse_bo_ko_payload(row["payload"])}
        for row in records.get("KO", [])
    ]

    contour_or_hole_records = {
        prefix: entries
        for prefix, entries in records.items()
        if prefix in {"AK", "BO", "SI", "IK", "KO", "PU"}
    }

    known_prefixes = {"ST", "EN", "AK", "B", "M", "L", "BO", "SI", "IK", "KO", "PU", "CM"}
    for prefix, entries in records.items():
        if prefix not in known_prefixes:
            unknown_records[prefix].extend(entries)

    return {
        "status": "ok",
        "file_path": source_path,
        "part_mark": part_mark,
        "member_identifier": part_mark,
        "profile": profile,
        "material": material,
        "overall_length": overall_length,
        "end_preparation": end_prep if end_prep else None,
        "contour_or_hole_records": contour_or_hole_records,
        "bo_records": bo_entries,
        "ko_records": ko_entries,
        "record_types": sorted(distinct_prefixes),
        "records": records,
        "unknown_records": unknown_records,
        "raw_summary": {
            "total_line_count": len(lines),
            "distinct_record_prefixes": sorted(distinct_prefixes),
            "unparsed_lines_count": unparsed_lines,
        },
    }


def inspect_nc1_file(path: str | Path) -> dict[str, Any]:
    """Inspect NC1 file path and return structured output."""
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    return inspect_nc1_text(text, source_path=str(file_path))
