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


def _wrapped_step_for_placement(placement: NestPlacement, cfg: EmiMachineProfile) -> float:
    is_round = (placement.profile_designation or "").upper().startswith("PIPE")
    return cfg.wrapped_step_degrees_round if is_round else cfg.wrapped_step_degrees_other


def _build_end_profile_x(
    *,
    kind: str,
    angle_deg: float,
    join_dia_in: float,
    od_in: float,
    step_deg: float,
    wall_thickness_in: float | None,
) -> list[tuple[float, float]]:
    radius = max(od_in / 2.0, 0.001)
    wall = max(0.001, min(radius * 0.95, wall_thickness_in if wall_thickness_in is not None else radius * 0.12))
    inner_radius = max(0.001, radius - wall)
    target_radius = max(0.001, join_dia_in / 2.0)
    step = max(0.5, step_deg)
    points: list[tuple[float, float]] = []
    a = 0.0
    while a <= 360.0001:
        t = math.radians(a)
        if kind == "cope":
            # Pipe intersection approximation (symmetrical around 0/180).
            lateral = radius * math.sin(t)
            radicand = max(0.0, target_radius * target_radius - lateral * lateral)
            intersect = math.sqrt(radicand)
            peak_intersect = target_radius
            cope_depth = peak_intersect - intersect
            cope_depth = min(cope_depth, radius - inner_radius + abs(math.sin(math.radians(angle_deg))) * wall)
            x = -cope_depth
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
    step_deg: float,
    wall_thickness_in: float | None,
) -> list[str]:
    kind = _classify_end_kind(angle_deg, join_dia_in, od_in, flat_cut)
    points = _build_end_profile_x(
        kind=kind,
        angle_deg=angle_deg,
        join_dia_in=join_dia_in,
        od_in=od_in,
        step_deg=step_deg,
        wall_thickness_in=wall_thickness_in,
    )
    lines = [
        f";{end_label} - Start ({kind})",
        f"(END GEOMETRY: angle={angle_deg:.3f} join_dia={join_dia_in:.3f} od={od_in:.3f})",
        f"G00 Z{cfg.safe_z_in:.4f}",
        f"G00 Z{cfg.pierce_z_in:.4f}",
        cfg.incremental_mode_command,
        cfg.wrapped_feed_mode_command,
    ]
    x0 = points[0][1]
    normalized = [(a_deg, x - x0) for a_deg, x in points]
    prev_a, prev_x = normalized[0]
    for a_deg, x in normalized[1:]:
        da = a_deg - prev_a
        dx = x - prev_x
        lines.append(f"G01 A{da:.4f} X{dx:.4f}")
        prev_a, prev_x = a_deg, x
    lines.extend([cfg.standard_feed_mode_command, cfg.absolute_mode_command, f";{end_label} - End"])
    return lines


def emit_pierce_step(cfg: EmiMachineProfile) -> list[str]:
    if cfg.pierce_step_in <= 0:
        return []
    return [f"G01 X{-cfg.pierce_step_in:.4f} F#29001"]


def emit_toe_step(cfg: EmiMachineProfile) -> list[str]:
    if cfg.toe_step_in <= 0:
        return []
    return [f"G01 X{cfg.toe_step_in:.4f} F#29001"]


def emit_lead_in(cfg: EmiMachineProfile) -> list[str]:
    if not cfg.lead_in_enabled or cfg.lead_in_x_in == 0:
        return []
    return [f"G01 X{cfg.lead_in_x_in:.4f} F#29001"]


def emit_lead_out(cfg: EmiMachineProfile) -> list[str]:
    lines: list[str] = []
    if cfg.lead_out_enabled and cfg.lead_out_x_in != 0:
        lines.append(f"G01 X{cfg.lead_out_x_in:.4f} F#29001")
    lines.append(f"G00 Z{cfg.retract_z_in:.4f}")
    return lines


def emit_end_reposition(placement: NestPlacement, cfg: EmiMachineProfile) -> list[str]:
    """Reposition from end1 to end2 with future compensation hooks."""
    compensation = cfg.toe_step_in + cfg.pierce_step_in + cfg.lead_out_x_in - cfg.lead_in_x_in
    traverse = placement.length_in + compensation
    return [
        ";End1->End2 Reposition",
        cfg.incremental_mode_command,
        f"G01 X{traverse:.4f} F#29001",
        cfg.absolute_mode_command,
        f"G00 A{placement.rotational_offset_deg:.4f}",
        f"G00 Z{cfg.pierce_z_in:.4f}",
    ]


def _emit_setup_stop(mode: str, phase: str, cfg: EmiMachineProfile) -> list[str]:
    if mode == "never":
        return []
    if mode == "first_stick_only" and phase == "program_start":
        return [cfg.setup_stop_command]
    if mode == "every_piece" and phase == "piece_start":
        return [cfg.setup_stop_command]
    if mode == "always":
        return [cfg.setup_stop_command]
    return []


def _emit_optional_fixture_commands(cfg: EmiMachineProfile) -> list[str]:
    lines: list[str] = []
    if cfg.emit_primary_chuck_commands and cfg.primary_chuck_close_command:
        lines.append(f"(OPTIONAL CHUCK: CLOSE)")
        lines.append(cfg.primary_chuck_close_command)
    if cfg.emit_part_sensor_air_blast:
        if cfg.part_sensor_air_on_command:
            lines.append("(OPTIONAL SENSOR AIR: ON)")
            lines.append(cfg.part_sensor_air_on_command)
        if cfg.material_staged_check_command:
            lines.append("(OPTIONAL MATERIAL CHECK)")
            lines.append(cfg.material_staged_check_command)
        if cfg.part_sensor_air_off_command:
            lines.append("(OPTIONAL SENSOR AIR: OFF)")
            lines.append(cfg.part_sensor_air_off_command)
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
    step_deg = _wrapped_step_for_placement(placement, cfg)
    lines = [
        f"(ROTATIONAL OFFSET: {placement.rotational_offset_deg:.3f})",
        f"(END1 FLAT: {'Y' if placement.end1_flat_cut else 'N'})",
        *emit_pierce_step(cfg),
        *emit_toe_step(cfg),
        *emit_lead_in(cfg),
        cfg.torch_on_command,
        * _emit_wrapped_cut_section(
            end_label="End1",
            angle_deg=end1_angle,
            join_dia_in=end1_join,
            od_in=od,
            flat_cut=placement.end1_flat_cut,
            cfg=cfg,
            step_deg=step_deg,
            wall_thickness_in=placement.wall_thickness_in,
        ),
        *emit_lead_out(cfg),
        cfg.torch_off_command,
        *emit_end_reposition(placement, cfg),
        f"(END2 FLAT: {'Y' if placement.end2_flat_cut else 'N'})",
        *emit_pierce_step(cfg),
        *emit_toe_step(cfg),
        *emit_lead_in(cfg),
        cfg.torch_on_command,
        * _emit_wrapped_cut_section(
            end_label="End2",
            angle_deg=end2_angle,
            join_dia_in=end2_join,
            od_in=od,
            flat_cut=placement.end2_flat_cut,
            cfg=cfg,
            step_deg=step_deg,
            wall_thickness_in=placement.wall_thickness_in,
        ),
        *emit_lead_out(cfg),
        cfg.torch_off_command,
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
    clamp_cmd = cfg.clamp_close_command or cfg.clamp_command
    lines: list[str] = [
        "%",
        f"(PROGRAM {part.part_mark})",
        f"(POST {cfg.post_label})",
        cfg.unit_command,
        cfg.work_offset_command,
        cfg.tool_select_command,
        cfg.tool_length_command,
        cfg.absolute_mode_command,
        cfg.torch_raise_command,
        f"#29001 = {cfg.process_feed_ipm:.0f}",
        f"#29002 = {cfg.rapid_feed_ipm:.0f}",
        f"(PART MARK: {part.part_mark})",
        f"(LENGTH: {part.length_in:.3f})",
        f"(OD: {part.outer_diameter_in:.3f} WALL: {part.wall_thickness_in:.3f})",
        cfg.initial_position_command,
        f"G01 Z{cfg.pierce_z_in:.4f} F#29001",
        clamp_cmd,
        *_emit_optional_fixture_commands(cfg),
        *_emit_setup_stop(cfg.setup_stop_mode, "program_start", cfg),
    ]
    lines.extend(_emit_piece_end_blocks(pseudo_placement, cfg))
    lines.extend(["(PROMPT REMOVE PART)", cfg.footer_command, "%"])
    return "\n".join(lines) + "\n"


def emit_nested_nest_to_emi(nest: LinearNest, profile: EmiMachineProfile | None = None) -> str:
    """Emit a usable nest-level EMI-oriented program from a packed linear nest.

    This uses known semantics from current NC1 + nesting data and keeps unknown
    machine behaviors explicit as comments, rather than writing blank placeholders.
    """
    cfg = profile or EmiMachineProfile()
    clamp_cmd = cfg.clamp_close_command or cfg.clamp_command
    lines: list[str] = [
        "%",
        f"(PROGRAM {nest.nest_id})",
        f"(POST {cfg.post_label})",
        cfg.unit_command,
        cfg.work_offset_command,
        cfg.tool_select_command,
        cfg.tool_length_command,
        cfg.absolute_mode_command,
        cfg.torch_raise_command,
        f"#29001 = {cfg.process_feed_ipm:.0f}",
        f"#29002 = {cfg.rapid_feed_ipm:.0f}",
        "(LOAD SEQUENCE)",
        cfg.initial_position_command,
        f"G01 Z{cfg.pierce_z_in:.4f} F#29001",
        clamp_cmd,
        *_emit_optional_fixture_commands(cfg),
        *_emit_setup_stop(cfg.setup_stop_mode, "program_start", cfg),
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
        lines.extend([cfg.absolute_mode_command, cfg.axis_reset_command, f"G00 X{placement.offset_in:.4f}"])
        lines.extend(_emit_setup_stop(cfg.setup_stop_mode, "piece_start", cfg))
        lines.extend(_emit_piece_end_blocks(placement, cfg))
        lines.append(f"G00 Z{cfg.safe_z_in:.4f}")
        lines.append(cfg.piece_complete_prompt)

    if cfg.emit_primary_chuck_commands and cfg.primary_chuck_open_command:
        lines.extend(["(OPTIONAL CHUCK: OPEN)", cfg.primary_chuck_open_command])
    lines.extend([cfg.nested_complete_prompt, cfg.footer_command, "%"])
    return "\n".join(lines) + "\n"


def emit_minimal_sample(program_id: str = "SAMPLE001") -> str:
    """Emit a synthetic minimal-looking EMI ROP V1.4-style CNC file."""
    sample = MachineProgram(program_id=program_id)
    return emit_program(sample)
