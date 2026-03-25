"""Project defaults for NC1-driven nesting behavior.

Defaults are intentionally configurable and should not be treated as immutable
machine truths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ProfileFamily(str, Enum):
    """Profile family classification used for stock defaults and nesting."""

    PIPE = "pipe"
    HSS = "hss"
    ANGLE = "angle"
    UNKNOWN = "unknown"


DEFAULT_STOCK_LENGTHS_IN: dict[ProfileFamily, float] = {
    ProfileFamily.PIPE: 252.0,
    ProfileFamily.HSS: 240.0,
    ProfileFamily.ANGLE: 240.0,
    ProfileFamily.UNKNOWN: 252.0,
}


@dataclass(slots=True)
class NestingDefaults:
    """Editable defaults for nesting and stock handling."""

    stock_lengths_in: dict[ProfileFamily, float] = field(default_factory=lambda: dict(DEFAULT_STOCK_LENGTHS_IN))
    apply_last_piece_cope_trim: bool = True
    last_piece_cope_trim_in: float = 0.25

    def stock_length_for(self, family: ProfileFamily) -> float:
        """Return default stock length for a profile family."""
        return self.stock_lengths_in.get(family, self.stock_lengths_in[ProfileFamily.UNKNOWN])
