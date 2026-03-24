"""Parser for extracting minimal tube geometry fields from NC1 text."""

from __future__ import annotations

from pathlib import Path
import re

from stptocnc.models import Nc1Part, TubeEndSpec

_FLOAT = r"([-+]?\d+(?:\.\d+)?)"


def _find_first_float(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _find_part_mark(text: str) -> str | None:
    patterns = [
        r"\b(?:PART\s*MARK|PIECE\s*MARK|MARK)\s*[:=]\s*([A-Za-z0-9_.-]+)",
        r"\bAK\s*[:=]?\s*([A-Za-z0-9_.-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def parse_nc1_text(text: str, source_path: str | None = None) -> Nc1Part:
    """Parse NC1 text into a simplified part model used by the EMI writer.

    This parser is intentionally permissive and pattern-based for bootstrap work.
    Unknown semantics should be refined once matched NC1/EMI datasets are added.
    """

    part_mark = _find_part_mark(text)

    od = _find_first_float(
        text,
        [
            rf"\b(?:OD|OUTER\s*DIAM(?:ETER)?)\s*[:=]\s*{_FLOAT}",
            rf"\bDIA\s*[:=]\s*{_FLOAT}",
        ],
    )
    wall = _find_first_float(
        text,
        [
            rf"\b(?:WALL(?:\s*THICKNESS)?|THK|T)\s*[:=]\s*{_FLOAT}",
        ],
    )
    length = _find_first_float(
        text,
        [
            rf"\b(?:LENGTH|LEN|L)\s*[:=]\s*{_FLOAT}",
        ],
    )

    end1_angle = _find_first_float(text, [rf"\b(?:END\s*1|E1)\s*ANGLE\s*[:=]\s*{_FLOAT}", rf"\bA1\s*[:=]\s*{_FLOAT}"])
    end1_join = _find_first_float(
        text,
        [rf"\b(?:END\s*1|E1)\s*(?:JOIN\s*)?DIA(?:METER)?\s*[:=]\s*{_FLOAT}", rf"\bJ1\s*[:=]\s*{_FLOAT}"],
    )

    end2_angle = _find_first_float(text, [rf"\b(?:END\s*2|E2)\s*ANGLE\s*[:=]\s*{_FLOAT}", rf"\bA2\s*[:=]\s*{_FLOAT}"])
    end2_join = _find_first_float(
        text,
        [rf"\b(?:END\s*2|E2)\s*(?:JOIN\s*)?DIA(?:METER)?\s*[:=]\s*{_FLOAT}", rf"\bJ2\s*[:=]\s*{_FLOAT}"],
    )

    missing: list[str] = []
    for name, value in [
        ("part mark", part_mark),
        ("outer diameter", od),
        ("wall thickness", wall),
        ("length", length),
        ("end1 angle", end1_angle),
        ("end1 join diameter", end1_join),
        ("end2 angle", end2_angle),
        ("end2 join diameter", end2_join),
    ]:
        if value is None:
            missing.append(name)

    if missing:
        raise ValueError(f"Unable to parse NC1 fields: {', '.join(missing)}")

    return Nc1Part(
        part_mark=str(part_mark),
        outer_diameter_in=float(od),
        wall_thickness_in=float(wall),
        length_in=float(length),
        end1=TubeEndSpec(angle_deg=float(end1_angle), join_diameter_in=float(end1_join)),
        end2=TubeEndSpec(angle_deg=float(end2_angle), join_diameter_in=float(end2_join)),
        source_path=source_path,
    )


def parse_nc1_file(path: str | Path) -> Nc1Part:
    """Parse a NC1 file from disk."""
    file_path = Path(path)
    return parse_nc1_text(file_path.read_text(encoding="utf-8"), source_path=str(file_path))
