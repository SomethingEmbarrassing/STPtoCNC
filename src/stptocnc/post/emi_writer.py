"""Synthetic EMI writer for early bootstrap milestones."""

from __future__ import annotations

import math

from stptocnc.config import EmiMachineProfile
from stptocnc.models import MachineProgram, Nc1Part
from stptocnc.models.nesting import LinearNest, NestPlacement
from stptocnc.post.emi_blocks import (
    CutSequenceBlock,
    FooterBlock,
    HeaderBlock,
    MachineSetupBlock,
    RemovePartPromptBlock,
)


def emit_program(program: MachineProgram) -> str:
    """Emit a minimal EMI-like text program from a structured model."""
    header = HeaderBlock(lines=program.header or [f"(PROGRAM {program.program_id})", f"(POST {program.post_family})"])
    setup = MachineSetupBlock(lines=program.setup or ["G90", "(SETUP PLACEHOLDER)"])
    cuts = CutSequenceBlock(lines=[f"(OP {op.op_id}) {op.description}" for op in program.operations])
    prompts = RemovePartPromptBlock(lines=program.prompts or ["(PROMPT REMOVE PART)"])
    footer = FooterBlock(lines=program.footer or ["M30", "%"])

    all_lines = [
        "%",
        *header.lines,
        *setup.lines,
        *cuts.lines,
        *prompts.lines,
        *footer.lines,
    ]
    return "\n".join(all_lines) + "\n"


def _classify_end_kind(angle_deg: float, join_dia_in: float, od_in: float, flat_cut: bool) -> str:
    if flat_cut:
        return "flat"
    if join_dia_in < od_in * 0.92:
        return "cope"
    if abs(angle_deg) > 1.0:
        return "miter"
    return "flat"


def _build_end_profile_x(
    *,
    kind: str,
    angle_deg: float,
    join_dia_in: float,
    od_in: float,
    step_deg: float,
) -> list[tuple[float, float]]:
    radius = max(od_in / 2.0, 0.001)
    step = max(0.5, step_deg)
    points: list[tuple[float, float]] = []
    a = 0.0
    while a <= 360.0001:
        t = math.radians(a)
        if kind == "cope":
            cope_depth = max(0.0, (od_in - max(0.0, join_dia_in)) / 2.0)
            angle_gain = abs(math.sin(math.radians(angle_deg))) * radius * 0.35
            x = -cope_depth * (1.0 - math.cos(t)) - angle_gain * math.cos(t)
        elif kind == "miter":
            slope = math.tan(math.radians(max(-80.0, min(80.0, angle_deg))))
            x = -radius * slope * math.cos(t)
        else:  # flat
            x = -radius * abs(math.sin(math.radians(angle_deg))) * 0.05 * math.cos(t)
        points.append((round(a, 4), x))
        a += step
    return points


def _emit_wrapped_cut_section(
    *,
    end_label: str,
    angle_deg: float,
    join_dia_in: float,
    od_in: float,
    flat_cut: bool,
    cfg: EmiMachineProfile,
) -> list[str]:
    kind = _classify_end_kind(angle_deg, join_dia_in, od_in, flat_cut)
    points = _build_end_profile_x(
        kind=kind,
        angle_deg=angle_deg,
        join_dia_in=join_dia_in,
        od_in=od_in,
        step_deg=cfg.wrapped_step_degrees,
    )
    lines = [
        f";{end_label} - Start ({kind})",
        f"(END GEOMETRY: angle={angle_deg:.3f} join_dia={join_dia_in:.3f} od={od_in:.3f})",
        f"G00 Z{cfg.safe_z_in:.4f}",
        f"G00 Z{cfg.pierce_z_in:.4f}",
        "G91",
        "G93.1",
    ]
    prev_a, prev_x = points[0]
    lines.append(f"G01 A{prev_a:.4f} X{prev_x:.4f} F#29001")
    for a_deg, x in points[1:]:
        da = a_deg - prev_a
        dx = x - prev_x
        lines.append(f"G01 A{da:.4f} X{dx:.4f} F#29002")
        prev_a, prev_x = a_deg, x
    lines.extend(["G94", "G90", f";{end_label} - End"])
    return lines


def _emit_piece_end_blocks(placement: NestPlacement, cfg: EmiMachineProfile) -> list[str]:
    end1_angle = placement.end1_angle_deg if placement.end1_angle_deg is not None else 0.0
    end1_join = placement.end1_join_diameter_in if placement.end1_join_diameter_in is not None else 0.0
    end2_angle = placement.end2_angle_deg if placement.end2_angle_deg is not None else 0.0
    end2_join = placement.end2_join_diameter_in if placement.end2_join_diameter_in is not None else 0.0
    od = placement.outer_diameter_in if placement.outer_diameter_in is not None else max(end1_join, end2_join, 1.0)
    if placement.end1_flat_cut:
        end1_join = 200.0
    if placement.end2_flat_cut:
        end2_join = 200.0
    lines = [
        f"(ROTATIONAL OFFSET: {placement.rotational_offset_deg:.3f})",
        f"(END1 FLAT: {'Y' if placement.end1_flat_cut else 'N'})",
        * _emit_wrapped_cut_section(
            end_label="End1",
            angle_deg=end1_angle,
            join_dia_in=end1_join,
            od_in=od,
            flat_cut=placement.end1_flat_cut,
            cfg=cfg,
        ),
        ";End1->End2 Reposition",
        f"G00 Z{cfg.safe_z_in:.4f}",
        "G91",
        f"G01 X{placement.length_in:.4f} F#29001",
        "G90",
        f"G00 A{placement.rotational_offset_deg:.4f}",
        f"G00 Z{cfg.pierce_z_in:.4f}",
        f"(END2 FLAT: {'Y' if placement.end2_flat_cut else 'N'})",
        * _emit_wrapped_cut_section(
            end_label="End2",
            angle_deg=end2_angle,
            join_dia_in=end2_join,
            od_in=od,
            flat_cut=placement.end2_flat_cut,
            cfg=cfg,
        ),
    ]
    return lines


def emit_nc1_part_to_emi(part: Nc1Part) -> str:
    """Emit a structurally valid EMI-style CNC file from parsed NC1 values."""
    cfg = EmiMachineProfile()
    pseudo_placement = NestPlacement(
        instance_id=f"{part.part_mark}#1",
        part_mark=part.part_mark,
        offset_in=0.0,
        length_in=part.length_in,
        end1_angle_deg=part.end1.angle_deg,
        end1_join_diameter_in=part.end1.join_diameter_in,
        end2_angle_deg=part.end2.angle_deg,
        end2_join_diameter_in=part.end2.join_diameter_in,
        end1_flat_cut=part.end1.flat_cut,
        end2_flat_cut=part.end2.flat_cut,
        rotational_offset_deg=part.rotational_offset_deg,
        outer_diameter_in=part.outer_diameter_in,
    )
    lines: list[str] = [
        "%",
        f"(PROGRAM {part.part_mark})",
        f"(POST {cfg.post_label})",
        cfg.unit_command,
        cfg.work_offset_command,
        cfg.tool_select_command,
        cfg.tool_length_command,
        "G90",
        cfg.torch_raise_command,
        f"#29001 = {cfg.process_feed_ipm:.0f}",
        f"#29002 = {cfg.rapid_feed_ipm:.0f}",
        f"(PART MARK: {part.part_mark})",
        f"(LENGTH: {part.length_in:.3f})",
        f"(OD: {part.outer_diameter_in:.3f} WALL: {part.wall_thickness_in:.3f})",
        f"G00 Y0.0 A0.0",
        f"G01 Z{cfg.pierce_z_in:.4f} F#29001",
        cfg.clamp_command,
        cfg.setup_stop_command,
    ]
    if cfg.torch_on_command:
        lines.append(cfg.torch_on_command)
    lines.extend(_emit_piece_end_blocks(pseudo_placement, cfg))
    if cfg.torch_off_command:
        lines.append(cfg.torch_off_command)
    lines.extend(["(PROMPT REMOVE PART)", cfg.footer_command, "%"])
    return "\n".join(lines) + "\n"


def emit_nested_nest_to_emi(nest: LinearNest, profile: EmiMachineProfile | None = None) -> str:
    """Emit a usable nest-level EMI-oriented program from a packed linear nest.

    This uses known semantics from current NC1 + nesting data and keeps unknown
    machine behaviors explicit as comments, rather than writing blank placeholders.
    """
    cfg = profile or EmiMachineProfile()
    lines: list[str] = [
        "%",
        f"(PROGRAM {nest.nest_id})",
        f"(POST {cfg.post_label})",
        cfg.unit_command,
        cfg.work_offset_command,
        cfg.tool_select_command,
        cfg.tool_length_command,
        "G90",
        cfg.torch_raise_command,
        f"#29001 = {cfg.process_feed_ipm:.0f}",
        f"#29002 = {cfg.rapid_feed_ipm:.0f}",
        "(LOAD SEQUENCE)",
        "G00 Y0.0 A0.0",
        f"G01 Z{cfg.pierce_z_in:.4f} F#29001",
        cfg.clamp_command,
        cfg.setup_stop_command,
        f"(NEST STOCK LENGTH IN: {nest.stock_length_in:.3f})",
        f"(NEST USED LENGTH IN: {nest.used_length_in:.3f})",
        f"(NEST REMAINING DROP IN: {nest.remaining_length_in:.3f})",
        "(NOTE: TRIM-CUT COMMAND IS CONFIGURABLE VIA EMI MACHINE PROFILE)",
    ]

    for cut_order, placement in enumerate(nest.placements, start=1):
        if cfg.torch_raise_command:
            lines.append(cfg.torch_raise_command)
        lines.append(
            f"(PIECE {cut_order}: {placement.part_mark} START={placement.offset_in:.3f} LEN={placement.length_in:.3f})"
        )
        if placement.transition_trim_before_in > 0:
            lines.append(
                f"(TRIM BEFORE PIECE: {placement.transition_trim_before_in:.3f} IN REASON={placement.transition_reason})"
            )
            if cfg.trim_cut_command:
                lines.append(cfg.trim_cut_command)
            else:
                lines.append("(TRIM CUT COMMAND NOT CONFIGURED)")
        lines.extend(["G90", "G92 X0.0", f"G00 X{placement.offset_in:.4f}"])
        if cfg.torch_on_command:
            lines.append(cfg.torch_on_command)
        lines.extend(_emit_piece_end_blocks(placement, cfg))
        if cfg.torch_off_command:
            lines.append(cfg.torch_off_command)
        lines.append(f"G00 Z{cfg.safe_z_in:.4f}")
        lines.append(cfg.piece_complete_prompt)

    lines.extend([cfg.nested_complete_prompt, cfg.footer_command, "%"])
    return "\n".join(lines) + "\n"


def emit_minimal_sample(program_id: str = "SAMPLE001") -> str:
    """Emit a synthetic minimal-looking EMI ROP V1.4-style CNC file."""
    sample = MachineProgram(program_id=program_id)
    return emit_program(sample)
