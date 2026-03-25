"""NC1-derived part models for early NC1 -> EMI conversion."""

from __future__ import annotations

from dataclasses import dataclass

from stptocnc.config import ProfileFamily


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
    quantity: int = 1
    quantity_source: str = "default"
    profile_designation: str | None = None
    profile_family: ProfileFamily = ProfileFamily.UNKNOWN
    source_path: str | None = None
