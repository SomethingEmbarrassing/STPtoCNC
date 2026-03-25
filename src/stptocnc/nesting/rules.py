"""Nesting rules and lightweight helpers."""

from __future__ import annotations

from dataclasses import dataclass

from stptocnc.config import NestingDefaults
from stptocnc.models.nesting import PartInstance


@dataclass(slots=True)
class TransitionDecision:
    """Result of adjacency compatibility inference between two part instances."""

    trim_before_next_in: float
    compatible: bool
    reason: str


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


def evaluate_adjacency(previous: PartInstance | None, nxt: PartInstance, defaults: NestingDefaults | None = None) -> TransitionDecision:
    """Infer whether adjacent pieces can touch directly or require trim.

    Assumptions:
    - first part on fresh stock starts on flat raw material (no leading trim)
    - unknown semantics default conservative (apply trim)
    """

    cfg = defaults or NestingDefaults()
    if previous is None:
        return TransitionDecision(trim_before_next_in=0.0, compatible=True, reason="fresh_stock_first_part")

    if not nxt.requires_flat_start:
        return TransitionDecision(trim_before_next_in=0.0, compatible=True, reason="next_part_does_not_require_flat_start")

    if previous.leaves_flat_remainder:
        return TransitionDecision(trim_before_next_in=0.0, compatible=True, reason="previous_end_flat_compatible")

    return TransitionDecision(
        trim_before_next_in=cfg.last_piece_cope_trim_in,
        compatible=False,
        reason="previous_end_not_flat_compatible",
    )
