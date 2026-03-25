"""Utilities for reverse-engineering EMI .CNC program text."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from pathlib import Path
from typing import Any

COMMENT_RE = re.compile(r"\((.*?)\)")
GCODE_RE = re.compile(r"\bG\d+(?:\.\d+)?\b", re.IGNORECASE)
MCODE_RE = re.compile(r"\bM\d+(?:\.\d+)?\b", re.IGNORECASE)
VAR_RE = re.compile(r"[#@]\w+|\b[A-Z]\w*\s*=\s*[-+]?\d+(?:\.\d+)?", re.IGNORECASE)
MOTION_RE = re.compile(r"\b[XYZABC][-+]?\d+(?:\.\d+)?\b", re.IGNORECASE)
PROMPT_RE = re.compile(r"\bPROMPT\b|\bREMOVE\b|\bOPERATOR\b", re.IGNORECASE)


@dataclass(slots=True)
class ParsedLine:
    """One interpreted line from a CNC file."""

    line_number: int
    raw: str
    comments: list[str] = field(default_factory=list)
    g_codes: list[str] = field(default_factory=list)
    m_codes: list[str] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)
    motion_words: list[str] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)

    @property
    def probable_section(self) -> str:
        """Best-effort section grouping for reverse engineering."""
        upper = self.raw.upper()
        if self.prompts:
            return "operator_prompts"
        if self.line_number <= 10 or "PROGRAM" in upper or "POST" in upper:
            return "header"
        if self.m_codes and any(code.upper() in {"M30", "M02"} for code in self.m_codes):
            return "footer"
        if self.motion_words or self.g_codes or self.m_codes:
            return "cut_sequence"
        return "setup_or_misc"

    def to_dict(self) -> dict[str, Any]:
        """Serialize parsed line to dictionary output."""
        return {
            "line_number": self.line_number,
            "raw": self.raw,
            "comments": self.comments,
            "g_codes": self.g_codes,
            "m_codes": self.m_codes,
            "variables": self.variables,
            "motion_words": self.motion_words,
            "prompts": self.prompts,
            "probable_section": self.probable_section,
        }


def inspect_cnc_text(text: str, source_path: str | None = None) -> dict[str, Any]:
    """Inspect CNC source text and return structured analysis."""
    parsed_lines: list[ParsedLine] = []
    section_counts: dict[str, int] = {}

    total_comments = 0
    total_variables = 0
    motion_line_count = 0
    prompt_line_count = 0
    g_codes: set[str] = set()
    m_codes: set[str] = set()

    for idx, raw_line in enumerate(text.splitlines(), start=1):
        parsed = ParsedLine(
            line_number=idx,
            raw=raw_line,
            comments=COMMENT_RE.findall(raw_line),
            g_codes=GCODE_RE.findall(raw_line),
            m_codes=MCODE_RE.findall(raw_line),
            variables=VAR_RE.findall(raw_line),
            motion_words=MOTION_RE.findall(raw_line),
            prompts=PROMPT_RE.findall(raw_line),
        )
        section = parsed.probable_section
        section_counts[section] = section_counts.get(section, 0) + 1

        total_comments += len(parsed.comments)
        total_variables += len(parsed.variables)
        if parsed.motion_words:
            motion_line_count += 1
        if parsed.prompts:
            prompt_line_count += 1
        g_codes.update(code.upper() for code in parsed.g_codes)
        m_codes.update(code.upper() for code in parsed.m_codes)

        parsed_lines.append(parsed)

    return {
        "status": "ok",
        "file_path": source_path,
        "line_count": len(parsed_lines),
        "sections": section_counts,
        "summary": {
            "comment_count": total_comments,
            "variable_count": total_variables,
            "motion_line_count": motion_line_count,
            "prompt_line_count": prompt_line_count,
            "g_codes": sorted(g_codes),
            "m_codes": sorted(m_codes),
        },
        "lines": [line.to_dict() for line in parsed_lines],
    }


def inspect_cnc_file(path: str | Path) -> dict[str, Any]:
    """Inspect a CNC file from disk."""
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    return inspect_cnc_text(text, source_path=str(file_path))
