"""Parser for extracting minimal tube geometry fields from NC1 text."""

from __future__ import annotations

from pathlib import Path
import re

from stptocnc.models import Nc1Part, TubeEndSpec

_FLOAT = r"([-+]?\d+(?:\.\d+)?)"
_MM_PER_IN = 25.4

_NOMINAL_PIPE_OD_IN: dict[float, float] = {
    0.5: 0.84,
    0.75: 1.05,
    1.0: 1.315,
    1.25: 1.66,
    1.5: 1.9,
    2.0: 2.375,
    2.5: 2.875,
    3.0: 3.5,
}


def _find_first_float(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _find_part_mark(text: str) -> str | None:
    patterns = [
        r"\b(?:PART\s*MARK|PIECE\s*MARK|MARK)\s*[:=]\s*([A-Za-z0-9_.-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _parse_pipe_profile_od_in(text: str) -> float | None:
    """Parse nominal pipe size from profile text like PIPE1-1/2SCH40."""
    match = re.search(r"PIPE\s*(\d+)(?:-(\d+)/(\d+))?", text, flags=re.IGNORECASE)
    if not match:
        return None

    whole = float(match.group(1))
    frac = 0.0
    if match.group(2) and match.group(3):
        frac = float(match.group(2)) / float(match.group(3))
    nominal = whole + frac

    return _NOMINAL_PIPE_OD_IN.get(nominal)


def _parse_tekla_style_fallback(text: str) -> dict[str, float | str | None]:
    """Extract values from unlabeled Tekla-like NC1 blocks as fallback."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    part_mark: str | None = None
    for line in lines:
        if re.fullmatch(r"[A-Za-z]{1,4}\d{2,}", line, flags=re.IGNORECASE):
            part_mark = line
            break

    od_in = _parse_pipe_profile_od_in(text)

    wall_mm = None
    length_mm = None
    if "B" in lines:
        b_idx = lines.index("B")
        numeric_after_b: list[float] = []
        for row in lines[b_idx + 1 : b_idx + 12]:
            try:
                numeric_after_b.append(float(row))
            except ValueError:
                continue
        if numeric_after_b:
            length_mm = max(numeric_after_b)
            small = [value for value in numeric_after_b if 1.0 <= value <= 20.0]
            if small:
                wall_mm = min(small)

    join_dia = None
    m = re.search(r"\bv\s*([-+]?\d+(?:\.\d+)?)u", text, flags=re.IGNORECASE)
    if m:
        join_dia = float(m.group(1))

    ak_rows: list[list[float]] = []
    in_ak = False
    for line in text.splitlines():
        raw = line.strip()
        if raw == "AK":
            in_ak = True
            continue
        if raw == "EN":
            in_ak = False
        if not in_ak or not raw:
            continue
        nums = re.findall(r"[-+]?\d+(?:\.\d+)?", raw)
        if len(nums) >= 4:
            ak_rows.append([float(n) for n in nums])

    end1_angle = None
    end2_angle = None
    if ak_rows:
        # Column 4 carries the strongest end-shape variation in sample files.
        half = max(1, len(ak_rows) // 2)
        col4_a = [abs(row[3]) for row in ak_rows[:half] if len(row) >= 4]
        col4_b = [abs(row[3]) for row in ak_rows[half:] if len(row) >= 4]
        end1_angle = max(col4_a) if col4_a else None
        end2_angle = max(col4_b) if col4_b else end1_angle

    return {
        "part_mark": part_mark,
        "od": od_in,
        "wall": (wall_mm / _MM_PER_IN) if wall_mm is not None else None,
        "length": (length_mm / _MM_PER_IN) if length_mm is not None else None,
        "end1_angle": end1_angle,
        "end2_angle": end2_angle,
        "end1_join": join_dia,
        "end2_join": join_dia,
    }


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

    fallback = _parse_tekla_style_fallback(text)
    part_mark = part_mark or fallback["part_mark"]
    od = od if od is not None else fallback["od"]
    wall = wall if wall is not None else fallback["wall"]
    length = length if length is not None else fallback["length"]
    end1_angle = end1_angle if end1_angle is not None else fallback["end1_angle"]
    end2_angle = end2_angle if end2_angle is not None else fallback["end2_angle"]
    end1_join = end1_join if end1_join is not None else fallback["end1_join"]
    end2_join = end2_join if end2_join is not None else fallback["end2_join"]

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
