"""CNC conformance checks against accepted shop outputs."""

from __future__ import annotations

from collections import Counter
from pathlib import Path


def _classify_line(raw: str) -> str | None:
    line = raw.strip()
    if not line:
        return None
    if line == "%":
        return "%"
    if line.startswith("(PROGRAM "):
        return "PROGRAM"
    if line.startswith("(POST "):
        return "POST"
    if line == "G90":
        return "G90"
    if line.startswith("(PIECE "):
        return "PIECE"
    if line.startswith("(TRIM BEFORE PIECE:"):
        return "TRIM BEFORE PIECE"
    if line.startswith("(PROMPT "):
        return "PROMPT"
    if line.startswith("M"):
        return line.split()[0]
    if line.startswith("A") and " X" in line:
        return "AX"
    if line.startswith("("):
        return "COMMENT"
    return "OTHER"


def _signature(path: str | Path) -> list[str]:
    text = Path(path).read_text(encoding="utf-8")
    tokens: list[str] = []
    for raw in text.splitlines():
        kind = _classify_line(raw)
        if kind is not None:
            tokens.append(kind)
    return tokens


def _is_subsequence(expected: list[str], observed: list[str]) -> tuple[bool, list[str]]:
    missing: list[str] = []
    i = 0
    for token in expected:
        found = False
        while i < len(observed):
            if observed[i] == token:
                found = True
                i += 1
                break
            i += 1
        if not found:
            missing.append(token)
    return (len(missing) == 0, missing)


def compare_cnc_conformance(generated_path: str | Path, accepted_path: str | Path) -> dict[str, object]:
    """Compare generated CNC structure against accepted shop output structure."""
    generated_sig = _signature(generated_path)
    accepted_sig = _signature(accepted_path)

    generated_counts = Counter(generated_sig)
    accepted_counts = Counter(accepted_sig)
    order_ok, missing_in_order = _is_subsequence(accepted_sig, generated_sig)

    count_mismatches = {
        token: {"expected": accepted_counts[token], "observed": generated_counts.get(token, 0)}
        for token in sorted(accepted_counts)
        if generated_counts.get(token, 0) != accepted_counts[token]
    }

    return {
        "status": "ok" if order_ok and not count_mismatches else "needs_review",
        "generated_path": str(generated_path),
        "accepted_path": str(accepted_path),
        "sequence_order_match": order_ok,
        "missing_sequence_tokens": missing_in_order,
        "count_mismatches": count_mismatches,
    }
