"""Excel cut list export for finalized nests."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from fractions import Fraction
from pathlib import Path
import re

from openpyxl import Workbook

from stptocnc.models.nesting import LinearNest


CUTLIST_COLUMNS = [
    "Nest ID",
    "Cut Order",
    "Piece Mark",
    "Material Shape",
    "Piece Length",
    "Start Offset",
    "Drop",
    "Trim Cut",
    "Notes",
    "Source File",
]


def normalize_material_shape(profile_designation: str | None) -> str:
    """Normalize material display for operator-friendly cut lists."""
    if not profile_designation:
        return "UNKNOWN"

    raw = " ".join(profile_designation.strip().upper().split())

    hss_match = re.match(r"^HSS\s*(.+)$", raw)
    if hss_match:
        return f"HSS{hss_match.group(1).replace(' ', '')}"

    if re.match(r"^L\d", raw):
        return raw

    angle_match = re.match(r"^ANGLE\s*([0-9].+)$", raw)
    if angle_match:
        return f"L{angle_match.group(1).replace(' ', '')}"

    size_pat = r"([0-9]+(?:\.[0-9]+)?(?:-[0-9]+/[0-9]+)?)"
    pipe_match = re.match(rf"^PIPE\s*{size_pat}\s*SCH\s*([0-9A-Z]+)$", raw)
    compact_match = re.match(rf"^PIPE{size_pat}SCH([0-9A-Z]+)$", raw)
    if pipe_match:
        return f"PIPE {pipe_match.group(1)} SCH {pipe_match.group(2)}"
    if compact_match:
        return f"PIPE {compact_match.group(1)} SCH {compact_match.group(2)}"

    return raw


def format_inches_fraction(value_in: float) -> str:
    """Format inches to nearest 1/16 for operator readability."""
    rounded = round(value_in * 16.0) / 16.0
    whole = int(rounded)
    frac = rounded - whole
    frac_part = Fraction(frac).limit_denominator(16)
    if frac_part.numerator == 0:
        return f'{whole}"'
    if whole == 0:
        return f'{frac_part.numerator}/{frac_part.denominator}"'
    return f'{whole} {frac_part.numerator}/{frac_part.denominator}"'


def format_feet_inches_fraction(value_in: float) -> str:
    """Format a length as feet + inches rounded to nearest 1/16."""
    rounded = round(value_in * 16.0) / 16.0
    feet = int(rounded // 12.0)
    inches_total = rounded - (feet * 12.0)
    whole_inches = int(inches_total)
    frac = inches_total - whole_inches
    frac_part = Fraction(frac).limit_denominator(16)

    if frac_part.numerator == 0:
        inch_display = f'{whole_inches}"'
    elif whole_inches == 0:
        inch_display = f'{frac_part.numerator}/{frac_part.denominator}"'
    else:
        inch_display = f'{whole_inches} {frac_part.numerator}/{frac_part.denominator}"'
    return f"{feet}'-{inch_display}"


def write_cutlist_workbook(nests: list[LinearNest], output_path: str | Path, report_dt: datetime | None = None) -> Path:
    """Write a single-sheet operator cut list workbook grouped by nest."""
    dt = report_dt or datetime.now()
    wb = Workbook()
    ws = wb.active
    ws.title = "CutList"

    nest_count = len(nests)
    piece_count = sum(len(n.placements) for n in nests)

    stock_counter: Counter[str] = Counter()
    for nest in nests:
        stock_shape = "UNKNOWN"
        if nest.placements:
            stock_shape = normalize_material_shape(nest.placements[0].profile_designation)
        key = f"{stock_shape} @ {format_inches_fraction(nest.stock_length_in)}"
        stock_counter[key] += 1

    ws.append(["Nest Cut List"])
    ws.append(["Date", dt.strftime("%Y-%m-%d")])
    ws.append(["Time", dt.strftime("%H:%M:%S")])
    ws.append(["Total Nests", nest_count])
    ws.append(["Total Pieces", piece_count])
    ws.append(["Raw Stock Summary", "; ".join(f"{k} qty {v}" for k, v in sorted(stock_counter.items()))])
    ws.append([])

    ws.append(CUTLIST_COLUMNS)

    for nest in nests:
        nest_filename = f"{nest.nest_id}.cnc"
        ws.append([f"Nest: {nest_filename}"])
        for order, placement in enumerate(nest.placements, start=1):
            drop = max(0.0, nest.stock_length_in - placement.end_in)
            notes = placement.transition_reason.replace("_", " ")
            ws.append(
                [
                    nest_filename,
                    order,
                    placement.part_mark,
                    normalize_material_shape(placement.profile_designation),
                    format_feet_inches_fraction(placement.length_in),
                    format_inches_fraction(placement.start_offset_in),
                    format_feet_inches_fraction(drop),
                    format_inches_fraction(placement.transition_trim_before_in),
                    notes,
                    placement.source_file,
                ]
            )
        ws.append([])

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out
