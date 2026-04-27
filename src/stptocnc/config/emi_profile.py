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
    torch_on_command: str = "M15"
    torch_off_command: str = "M16"
    torch_raise_command: str = "M25"
    piece_complete_prompt: str = "(PIECE COMPLETE)"
    nested_complete_prompt: str = "(PROMPT REMOVE NESTED STOCK)"
    footer_command: str = "M30"
    unit_command: str = "G20"
    work_offset_command: str = "G58"
    tool_select_command: str = "T1"
    tool_length_command: str = "G43 H1"
    clamp_command: str = "M10"
    absolute_mode_command: str = "G90"
    incremental_mode_command: str = "G91"
    wrapped_feed_mode_command: str = "G01 G93.1 F#29002"
    standard_feed_mode_command: str = "G94"
    axis_reset_command: str = "G92 X0.0"
    initial_position_command: str = "G00 Y0.0 A0.0"
    setup_stop_command: str = "M00"
    process_feed_ipm: float = 140.0
    rapid_feed_ipm: float = 14400.0
    wrapped_step_degrees_round: float = 3.21429
    wrapped_step_degrees_other: float = 3.21429
    safe_z_in: float = 4.0
    pierce_z_in: float = 2.0
    retract_z_in: float = 4.0
    setup_stop_mode: str = "always"  # always | first_stick_only | every_piece | never
    pierce_step_in: float = 0.001
    toe_step_in: float = 0.0002
    lead_in_x_in: float = 0.0
    lead_out_x_in: float = 0.0
    lead_in_enabled: bool = True
    lead_out_enabled: bool = True

    @classmethod
    def from_json_file(cls, path: str | Path) -> "EmiMachineProfile":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        defaults = cls()
        return cls(
            post_label=payload.get("post_label", defaults.post_label),
            trim_cut_command=payload.get("trim_cut_command"),
            torch_on_command=payload.get("torch_on_command", defaults.torch_on_command),
            torch_off_command=payload.get("torch_off_command", defaults.torch_off_command),
            torch_raise_command=payload.get("torch_raise_command", defaults.torch_raise_command),
            piece_complete_prompt=payload.get("piece_complete_prompt", defaults.piece_complete_prompt),
            nested_complete_prompt=payload.get("nested_complete_prompt", defaults.nested_complete_prompt),
            footer_command=payload.get("footer_command", defaults.footer_command),
            unit_command=payload.get("unit_command", defaults.unit_command),
            work_offset_command=payload.get("work_offset_command", defaults.work_offset_command),
            tool_select_command=payload.get("tool_select_command", defaults.tool_select_command),
            tool_length_command=payload.get("tool_length_command", defaults.tool_length_command),
            clamp_command=payload.get("clamp_command", defaults.clamp_command),
            absolute_mode_command=payload.get("absolute_mode_command", defaults.absolute_mode_command),
            incremental_mode_command=payload.get("incremental_mode_command", defaults.incremental_mode_command),
            wrapped_feed_mode_command=payload.get("wrapped_feed_mode_command", defaults.wrapped_feed_mode_command),
            standard_feed_mode_command=payload.get("standard_feed_mode_command", defaults.standard_feed_mode_command),
            axis_reset_command=payload.get("axis_reset_command", defaults.axis_reset_command),
            initial_position_command=payload.get("initial_position_command", defaults.initial_position_command),
            setup_stop_command=payload.get("setup_stop_command", defaults.setup_stop_command),
            process_feed_ipm=float(payload.get("process_feed_ipm", defaults.process_feed_ipm)),
            rapid_feed_ipm=float(payload.get("rapid_feed_ipm", defaults.rapid_feed_ipm)),
            wrapped_step_degrees_round=float(payload.get("wrapped_step_degrees_round", payload.get("wrapped_step_degrees", defaults.wrapped_step_degrees_round))),
            wrapped_step_degrees_other=float(payload.get("wrapped_step_degrees_other", defaults.wrapped_step_degrees_other)),
            safe_z_in=float(payload.get("safe_z_in", defaults.safe_z_in)),
            pierce_z_in=float(payload.get("pierce_z_in", defaults.pierce_z_in)),
            retract_z_in=float(payload.get("retract_z_in", defaults.retract_z_in)),
            setup_stop_mode=str(payload.get("setup_stop_mode", defaults.setup_stop_mode)),
            pierce_step_in=float(payload.get("pierce_step_in", defaults.pierce_step_in)),
            toe_step_in=float(payload.get("toe_step_in", defaults.toe_step_in)),
            lead_in_x_in=float(payload.get("lead_in_x_in", defaults.lead_in_x_in)),
            lead_out_x_in=float(payload.get("lead_out_x_in", defaults.lead_out_x_in)),
            lead_in_enabled=bool(payload.get("lead_in_enabled", defaults.lead_in_enabled)),
            lead_out_enabled=bool(payload.get("lead_out_enabled", defaults.lead_out_enabled)),
        )
