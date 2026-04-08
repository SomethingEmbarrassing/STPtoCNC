"""Synthetic EMI writer for early bootstrap milestones."""

from __future__ import annotations

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


def _emit_placeholder_end_loop(end_label: str, angle_deg: float, join_dia_in: float) -> list[str]:
    """Emit a 64-step placeholder A/X loop for one end profile."""
    lines = [f"({end_label}: angle={angle_deg:.3f} join_dia={join_dia_in:.3f})"]
    for step in range(64):
        a_deg = step * (360.0 / 64.0)
        x_val = -join_dia_in / 2.0
        lines.append(f"A{a_deg:.3f} X{x_val:.4f}")
    return lines


def _emit_placement_end_loops(placement: NestPlacement) -> list[str]:
    end1_angle = placement.end1_angle_deg if placement.end1_angle_deg is not None else 0.0
    end1_join = placement.end1_join_diameter_in if placement.end1_join_diameter_in is not None else 0.0
    end2_angle = placement.end2_angle_deg if placement.end2_angle_deg is not None else 0.0
    end2_join = placement.end2_join_diameter_in if placement.end2_join_diameter_in is not None else 0.0
    if placement.end1_flat_cut:
        end1_join = 200.0
    if placement.end2_flat_cut:
        end2_join = 200.0
    return [
        f"(ROTATIONAL OFFSET: {placement.rotational_offset_deg:.3f})",
        f"(END1 FLAT: {'Y' if placement.end1_flat_cut else 'N'})",
        * _emit_placeholder_end_loop("END1", end1_angle, end1_join),
        f"(END2 FLAT: {'Y' if placement.end2_flat_cut else 'N'})",
        * _emit_placeholder_end_loop("END2", end2_angle, end2_join),
    ]


def emit_nc1_part_to_emi(part: Nc1Part) -> str:
    """Emit a structurally valid EMI-style CNC file from parsed NC1 values."""
    lines: list[str] = [
        "%",
        f"(PROGRAM {part.part_mark})",
        "(POST EMI 2400 PROMPTS ROP V1.4)",
        "G90",
        f"(PART MARK: {part.part_mark})",
        f"(LENGTH: {part.length_in:.3f})",
        f"(OD: {part.outer_diameter_in:.3f} WALL: {part.wall_thickness_in:.3f})",
    ]

    lines.extend(_emit_placeholder_end_loop("END1", part.end1.angle_deg, part.end1.join_diameter_in))
    lines.extend(_emit_placeholder_end_loop("END2", part.end2.angle_deg, part.end2.join_diameter_in))

    lines.extend(["(PROMPT REMOVE PART)", "M30", "%"])
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
        "G90",
        "(PIECEMAKER MANUAL REF: TORCH M15/M16, TORCH RAISE M25)",
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
        if cfg.torch_on_command:
            lines.append(cfg.torch_on_command)
        lines.extend(_emit_placement_end_loops(placement))
        if cfg.torch_off_command:
            lines.append(cfg.torch_off_command)
        lines.append(cfg.piece_complete_prompt)

    lines.extend([cfg.nested_complete_prompt, cfg.footer_command, "%"])
    return "\n".join(lines) + "\n"


def emit_minimal_sample(program_id: str = "SAMPLE001") -> str:
    """Emit a synthetic minimal-looking EMI ROP V1.4-style CNC file."""
    sample = MachineProgram(program_id=program_id)
    return emit_program(sample)
