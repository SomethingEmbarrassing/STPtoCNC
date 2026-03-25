"""Linear nesting domain models for NC1-driven workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from stptocnc.config import NestingDefaults, ProfileFamily


class EndCondition(str, Enum):
    """Simplified part-end condition classification for adjacency inference."""

    FLAT = "flat"
    MITER = "miter"
    COPE = "cope"
    FISHMOUTH = "fishmouth"
    SADDLE = "saddle"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class PartInstance:
    """One consumable instance expanded from part quantity."""

    instance_id: str
    part_mark: str
    length_in: float
    profile_family: ProfileFamily
    start_condition: EndCondition = EndCondition.FLAT
    end_condition: EndCondition = EndCondition.UNKNOWN

    @property
    def requires_flat_start(self) -> bool:
        """Whether this part should start on a flat/raw segment."""
        return self.start_condition in {EndCondition.FLAT, EndCondition.MITER, EndCondition.UNKNOWN}

    @property
    def leaves_flat_remainder(self) -> bool:
        """Whether this part end leaves flat-compatible stock for adjacency."""
        return self.end_condition in {EndCondition.FLAT, EndCondition.MITER}


@dataclass(slots=True)
class NestPlacement:
    """Linear offset placement of one part instance on a stock stick."""

    instance_id: str
    part_mark: str
    offset_in: float
    length_in: float
    transition_trim_before_in: float = 0.0
    transition_reason: str = ""

    @property
    def end_in(self) -> float:
        """Placement end coordinate in inches."""
        return self.offset_in + self.length_in

    @property
    def consumed_length_in(self) -> float:
        """Raw stock consumed by this placement and its leading transition trim."""
        return self.transition_trim_before_in + self.length_in


@dataclass(slots=True)
class LinearNest:
    """One stock stick with linear placements for future UI bar/strip rendering."""

    nest_id: str
    profile_family: ProfileFamily
    stock_length_in: float
    placements: list[NestPlacement] = field(default_factory=list)

    @property
    def used_length_in(self) -> float:
        """Total used stock including transition trims between adjacent parts."""
        return sum(p.consumed_length_in for p in self.placements)

    @property
    def remaining_length_in(self) -> float:
        """Remaining stock on this stick."""
        return max(0.0, self.stock_length_in - self.used_length_in)

    @property
    def utilization_ratio(self) -> float:
        """Used fraction of stock length."""
        if self.stock_length_in <= 0:
            return 0.0
        return self.used_length_in / self.stock_length_in


@dataclass(slots=True)
class NestingResult:
    """Output bundle for first-pass deterministic linear nesting."""

    nests: list[LinearNest]


def infer_end_condition_from_nc1(part: "Nc1Part") -> EndCondition:
    """Infer a coarse end condition from currently-available NC1 part fields.

    TODO: replace heuristic with robust feature-based extraction from NC1 records.
    """
    angle = abs(part.end2.angle_deg)
    if part.end2.join_diameter_in <= part.outer_diameter_in * 0.8:
        return EndCondition.COPE
    if angle <= 1.0:
        return EndCondition.FLAT
    if angle < 89.0:
        return EndCondition.MITER
    return EndCondition.UNKNOWN


def infer_start_condition_from_nc1(part: "Nc1Part") -> EndCondition:
    """Infer a coarse start condition requirement from NC1 part fields.

    TODO: replace heuristic with robust start-feature parsing.
    """
    angle = abs(part.end1.angle_deg)
    if part.end1.join_diameter_in <= part.outer_diameter_in * 0.8:
        return EndCondition.COPE
    if angle <= 1.0:
        return EndCondition.FLAT
    if angle < 89.0:
        return EndCondition.MITER
    return EndCondition.UNKNOWN


def expand_part_instances(parts: list["Nc1Part"]) -> list[PartInstance]:
    """Expand NC1 part quantities into explicit linear nesting instances."""
    instances: list[PartInstance] = []
    for part in parts:
        qty = max(1, part.quantity)
        for index in range(qty):
            instances.append(
                PartInstance(
                    instance_id=f"{part.part_mark}#{index + 1}",
                    part_mark=part.part_mark,
                    length_in=part.length_in,
                    profile_family=part.profile_family,
                    start_condition=infer_start_condition_from_nc1(part),
                    end_condition=infer_end_condition_from_nc1(part),
                )
            )
    return instances


def default_stock_length_for_family(family: ProfileFamily, defaults: NestingDefaults | None = None) -> float:
    """Resolve stock default by profile family with editable override support."""
    cfg = defaults or NestingDefaults()
    return cfg.stock_length_for(family)
