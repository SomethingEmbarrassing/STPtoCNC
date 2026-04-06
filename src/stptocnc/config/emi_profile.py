"""Configurable EMI machine profile for shop/manual-specific command mapping."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(slots=True)
class EmiMachineProfile:
    """Machine/post command mapping loaded from shop documentation."""

    post_label: str = "EMI 2400 PROMPTS ROP V1.4"
    trim_cut_command: str | None = None
    piece_complete_prompt: str = "(PIECE COMPLETE)"
    nested_complete_prompt: str = "(PROMPT REMOVE NESTED STOCK)"
    footer_command: str = "M30"

    @classmethod
    def from_json_file(cls, path: str | Path) -> "EmiMachineProfile":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            post_label=payload.get("post_label", cls.post_label),
            trim_cut_command=payload.get("trim_cut_command"),
            piece_complete_prompt=payload.get("piece_complete_prompt", cls.piece_complete_prompt),
            nested_complete_prompt=payload.get("nested_complete_prompt", cls.nested_complete_prompt),
            footer_command=payload.get("footer_command", cls.footer_command),
        )
