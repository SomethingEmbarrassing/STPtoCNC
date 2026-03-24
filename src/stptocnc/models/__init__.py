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
]

from .nc1_part import Nc1Part, TubeEndSpec
