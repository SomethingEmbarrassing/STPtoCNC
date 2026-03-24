"""Synthetic EMI writer for early bootstrap milestones."""

from __future__ import annotations

from stptocnc.models import MachineProgram
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


def emit_minimal_sample(program_id: str = "SAMPLE001") -> str:
    """Emit a synthetic minimal-looking EMI ROP V1.4-style CNC file."""
    sample = MachineProgram(program_id=program_id)
    return emit_program(sample)
