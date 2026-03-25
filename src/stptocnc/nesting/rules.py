"""Nesting rules and lightweight helpers."""

from __future__ import annotations

from stptocnc.config import NestingDefaults


def trim_cut_for_last_piece(end_condition: str | None, defaults: NestingDefaults | None = None) -> float:
    """Return tail trim cut length for final piece per configured rule.

    Rule:
    - If last piece ends with a cope -> apply trim cut (default 0.25 in)
    - If last piece ends flat -> no trim

    TODO: integrate with real NC1/CNC-derived end-condition detection.
    """

    cfg = defaults or NestingDefaults()
    if not cfg.apply_last_piece_cope_trim:
        return 0.0

    normalized = (end_condition or "").strip().lower()
    if normalized in {"cope", "fishmouth", "saddle"}:
        return cfg.last_piece_cope_trim_in
    if normalized in {"flat", "straight", "miter"}:
        return 0.0
    return 0.0
