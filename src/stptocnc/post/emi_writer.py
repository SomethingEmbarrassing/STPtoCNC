"""Synthetic EMI writer for early bootstrap milestones."""

from __future__ import annotations

from stptocnc.models import MachineProgram, Nc1Part
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


def emit_minimal_sample(program_id: str = "SAMPLE001") -> str:
    """Emit a synthetic minimal-looking EMI ROP V1.4-style CNC file."""
    sample = MachineProgram(program_id=program_id)
    return emit_program(sample)
