"""Linear nesting domain models for NC1-driven workflows."""

from __future__ import annotations

from dataclasses import dataclass, field

from stptocnc.config import NestingDefaults, ProfileFamily


@dataclass(slots=True)
class PartInstance:
    """One consumable instance expanded from part quantity."""

    instance_id: str
    part_mark: str
    length_in: float
    profile_family: ProfileFamily
    end_condition: str | None = None


@dataclass(slots=True)
class NestPlacement:
    """Linear offset placement of one part instance on a stock stick."""

    instance_id: str
    part_mark: str
    offset_in: float
    length_in: float

    @property
    def end_in(self) -> float:
        """Placement end coordinate in inches."""
        return self.offset_in + self.length_in


@dataclass(slots=True)
class LinearNest:
    """One stock stick with linear placements for future UI bar/strip rendering."""

    nest_id: str
    profile_family: ProfileFamily
    stock_length_in: float
    placements: list[NestPlacement] = field(default_factory=list)
    trim_cut_in: float = 0.0

    @property
    def used_length_in(self) -> float:
        """Total used stock including trim cut at tail when configured."""
        if not self.placements:
            return self.trim_cut_in
        return max(p.end_in for p in self.placements) + self.trim_cut_in

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
                    # TODO: replace placeholder with real end-condition extraction.
                    end_condition="unknown",
                )
            )
    return instances


def default_stock_length_for_family(family: ProfileFamily, defaults: NestingDefaults | None = None) -> float:
    """Resolve stock default by profile family with editable override support."""
    cfg = defaults or NestingDefaults()
    return cfg.stock_length_for(family)
