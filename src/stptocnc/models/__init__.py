"""Domain models used across import, analysis, nesting, and post layers."""

from .core import (
    EndCut,
    EndCutType,
    FeatureType,
    HoleFeature,
    MachineOperation,
    MachineProgram,
    Nest,
    NestPartPlacement,
    Part,
    PartFeature,
    TubeProfile,
)
from .nc1_part import Nc1Part, TubeEndSpec
from .nesting import (
    EndCondition,
    LinearNest,
    NestPlacement,
    NestingResult,
    PartInstance,
    default_stock_length_for_family,
    expand_part_instances,
)

__all__ = [
    "EndCut",
    "EndCutType",
    "FeatureType",
    "HoleFeature",
    "MachineOperation",
    "MachineProgram",
    "Nest",
    "NestPartPlacement",
    "Part",
    "PartFeature",
    "TubeProfile",
    "Nc1Part",
    "TubeEndSpec",
    "EndCondition",
    "LinearNest",
    "NestPlacement",
    "NestingResult",
    "PartInstance",
    "expand_part_instances",
    "default_stock_length_for_family",
]
