"""EMI 2400 ROP V1.4-oriented program block abstractions.

These classes are intentionally lightweight wrappers around text lines so the
team can iteratively refine real machine semantics using archived samples.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class HeaderBlock:
    """Program header and identity lines."""

    lines: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MachineSetupBlock:
    """Machine setup lines such as mode and stock setup."""

    lines: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CutSequenceBlock:
    """Primary cut and motion-related lines."""

    lines: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RemovePartPromptBlock:
    """Operator prompt lines (e.g., remove/clear part prompts)."""

    lines: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FooterBlock:
    """Program end and teardown lines."""

    lines: list[str] = field(default_factory=list)
