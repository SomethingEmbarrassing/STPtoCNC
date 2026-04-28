"""Core domain models for STPtoCNC.

These models intentionally keep unknown or machine-specific semantics explicit,
so they can be refined as real EMI and geometry samples are integrated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FeatureType(str, Enum):
    """Supported part feature categories for early milestones."""

    END_CUT = "end_cut"
    HOLE = "hole"
    UNKNOWN = "unknown"


class EndCutType(str, Enum):
    """End-cut classifications for round tube workflows."""

    STRAIGHT = "straight"
    MITER = "miter"
    FISHMOUTH = "fishmouth"
    SADDLE = "saddle"
    COPE = "cope"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class TubeProfile:
    """Tube stock/profile information for a part."""

    outer_diameter_in: float
    wall_thickness_in: float | None = None
    material: str | None = None
    shape: str = "round"


@dataclass(slots=True)
class PartFeature:
    """Base feature type with an extension payload for unknown semantics."""

    id: str
    feature_type: FeatureType
    station_in: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EndCut(PartFeature):
    """Represents one tube end cut operation."""

    cut_type: EndCutType = EndCutType.UNKNOWN
    angle_deg: float | None = None
    rotation_deg: float | None = None

    def __post_init__(self) -> None:
        self.feature_type = FeatureType.END_CUT


@dataclass(slots=True)
class HoleFeature(PartFeature):
    """Represents a simple hole operation on tube stock."""

    diameter_in: float = 0.0
    axial_in: float = 0.0
    radial_angle_deg: float = 0.0

    def __post_init__(self) -> None:
        self.feature_type = FeatureType.HOLE
        self.station_in = self.axial_in


@dataclass(slots=True)
class Part:
    """Manufacturable part definition independent of source format."""

    part_id: str
    name: str
    length_in: float
    profile: TubeProfile
    features: list[PartFeature] = field(default_factory=list)
    source: str | None = None


@dataclass(slots=True)
class NestPartPlacement:
    """Placement of a part in a nested stock stick."""

    part_id: str
    start_station_in: float
    end_station_in: float
    quantity: int = 1


@dataclass(slots=True)
class Nest:
    """Represents one production stick program with multiple parts."""

    nest_id: str
    stock_length_in: float = 252.0
    chuck_loss_in: float = 0.0
    leading_scrap_in: float = 0.0
    trailing_scrap_in: float = 0.0
    min_gap_in: float = 0.0
    placements: list[NestPartPlacement] = field(default_factory=list)


@dataclass(slots=True)
class MachineOperation:
    """Low-level operation for post processing and emission."""

    op_id: str
    kind: str
    description: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MachineProgram:
    """Structured representation of one EMI program output."""

    program_id: str
    post_family: str = "EMI 2400 PROMPTS ROP V1.4"
    header: list[str] = field(default_factory=list)
    setup: list[str] = field(default_factory=list)
    operations: list[MachineOperation] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)
    footer: list[str] = field(default_factory=list)
