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
    4.0: 4.5,
    5.0: 5.563,
    6.0: 6.625,
    8.0: 8.625,
}


def _find_first_float(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _fraction_to_float(chunk: str) -> float:
    if "/" in chunk:
        a, b = chunk.split("/", 1)
        return float(a) / float(b)
    return float(chunk)


def _find_part_mark(text: str) -> str | None:
    patterns = [
        r"\b(?:PART\s*MARK|PIECE\s*MARK|MARK)\s*[:=]\s*([A-Za-z0-9_.-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _parse_profile_dims(text: str) -> dict[str, float | str] | None:
    """Parse common shape designations (PIPE/HSS/L) into simple dimensions."""
    upper = text.upper()

    pipe_match = re.search(r"PIPE\s*(\d+)(?:-(\d+)/(\d+))?", upper)
    if pipe_match:
        whole = float(pipe_match.group(1))
        frac = 0.0
        if pipe_match.group(2) and pipe_match.group(3):
            frac = float(pipe_match.group(2)) / float(pipe_match.group(3))
        nominal = whole + frac
        od = _NOMINAL_PIPE_OD_IN.get(nominal)
        return {"shape": "pipe", "nominal_in": nominal, "od_in": od} if od else None

    hss_match = re.search(r"HSS\s*(\d+(?:\.\d+)?)X(\d+(?:\.\d+)?)X(\d+(?:/\d+)?|\d+(?:\.\d+)?)", upper)
    if hss_match:
        dim1 = float(hss_match.group(1))
        dim2 = float(hss_match.group(2))
        wall = _fraction_to_float(hss_match.group(3))
        return {"shape": "hss", "od_in": max(dim1, dim2), "wall_in": wall, "height_in": dim1, "width_in": dim2}

    l_match = re.search(r"\bL\s*(\d+(?:\.\d+)?)X(\d+(?:\.\d+)?)X(\d+(?:/\d+)?|\d+(?:\.\d+)?)", upper)
    if l_match:
        leg1 = float(l_match.group(1))
        leg2 = float(l_match.group(2))
        thick = _fraction_to_float(l_match.group(3))
        return {"shape": "angle", "od_in": max(leg1, leg2), "wall_in": thick, "leg1_in": leg1, "leg2_in": leg2}

    return None


def _extract_section_numeric(lines: list[str], section_names: tuple[str, ...]) -> list[float]:
    values: list[float] = []
    for i, line in enumerate(lines):
        if line.strip() in section_names:
            for row in lines[i + 1 : i + 20]:
                s = row.strip()
                if not s:
                    continue
                try:
                    values.append(float(s))
                except ValueError:
                    break
    return values


def _parse_tekla_style_fallback(text: str) -> dict[str, float | str | None]:
    """Extract values from unlabeled Tekla-like NC1 blocks as fallback."""
    lines = [line.rstrip() for line in text.splitlines()]
    non_empty = [line.strip() for line in lines if line.strip()]

    part_mark: str | None = None
    for line in non_empty:
        if re.fullmatch(r"[A-Za-z]{1,4}\d{2,}", line, flags=re.IGNORECASE):
            part_mark = line
            break

    # profile string candidate and profile-derived dimensions
    profile_line = next((line for line in non_empty if re.search(r"^(PIPE|HSS|L\d)", line, flags=re.IGNORECASE)), None)
    profile_dims = _parse_profile_dims(profile_line or "") if profile_line else None

    od_in = profile_dims.get("od_in") if profile_dims else None
    wall_in = profile_dims.get("wall_in") if profile_dims and "wall_in" in profile_dims else None

    # Numeric section payloads vary by shape type (B/M/L)
    section_values = _extract_section_numeric(lines, ("B", "M", "L"))
    length_mm = max(section_values) if section_values else None

    if wall_in is None and section_values:
        small = [value for value in section_values if 1.0 <= value <= 20.0]
        if small:
            wall_in = min(small) / _MM_PER_IN

    join_dia = None
    m = re.search(r"\bv\s*([-+]?\d+(?:\.\d+)?)\s*[uohs]", text, flags=re.IGNORECASE)
    if m:
        join_dia = float(m.group(1))

    # KO/BO fallback can provide additional diameter-like values.
    bo_diams: list[float] = []
    for line in non_empty:
        if line.startswith(("h", "v", "u", "o")) and any(tag in text for tag in ["BO", "KO"]):
            nums = re.findall(r"[-+]?\d+(?:\.\d+)?", line)
            if len(nums) >= 3:
                bo_diams.append(float(nums[-1]))
    if join_dia is None and bo_diams:
        join_dia = max(bo_diams) / _MM_PER_IN

    ak_rows: list[list[float]] = []
    in_ak = False
    for line in lines:
        raw = line.strip()
        if raw == "AK":
            in_ak = True
            continue
        if raw in {"EN", "BO", "KO", "SI", "ST"}:
            in_ak = False
        if not in_ak or not raw:
            continue
        nums = re.findall(r"[-+]?\d+(?:\.\d+)?", raw)
        if len(nums) >= 4:
            ak_rows.append([float(n) for n in nums])

    end1_angle = 0.0
    end2_angle = 0.0
    if ak_rows:
        half = max(1, len(ak_rows) // 2)
        col4_a = [abs(row[3]) for row in ak_rows[:half] if len(row) >= 4]
        col4_b = [abs(row[3]) for row in ak_rows[half:] if len(row) >= 4]
        end1_angle = max(col4_a) if col4_a else 0.0
        end2_angle = max(col4_b) if col4_b else end1_angle

    if join_dia is None and od_in is not None:
        join_dia = float(od_in)

    return {
        "part_mark": part_mark,
        "od": float(od_in) if od_in is not None else None,
        "wall": float(wall_in) if wall_in is not None else None,
        "length": (float(length_mm) / _MM_PER_IN) if length_mm is not None else None,
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
