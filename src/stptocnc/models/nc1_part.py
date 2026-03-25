"""NC1-derived part models for early NC1 -> EMI conversion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TubeEndSpec:
    """Represents a tube end join profile in simplified form."""

    angle_deg: float
    join_diameter_in: float


@dataclass(slots=True)
class Nc1Part:
    """Minimal part model extracted from NC1 for v1 conversion passes."""

    part_mark: str
    outer_diameter_in: float
    wall_thickness_in: float
    length_in: float
    end1: TubeEndSpec
    end2: TubeEndSpec
    source_path: str | None = None
