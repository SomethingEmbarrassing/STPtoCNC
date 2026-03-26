"""Excel cut list export for finalized nests."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
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

    raw = profile_designation.strip().upper()

    if raw.startswith("HSS"):
        return raw

    if re.match(r"^L\d", raw):
        return raw

    pipe_match = re.match(r"^PIPE\s*([0-9]+(?:-[0-9]+/[0-9]+)?)\s*SCH\s*([0-9A-Z]+)", raw)
    compact_match = re.match(r"^PIPE([0-9]+(?:-[0-9]+/[0-9]+)?)SCH([0-9A-Z]+)", raw)
    if pipe_match:
        return f"PIPE {pipe_match.group(1)} SCH {pipe_match.group(2)}"
    if compact_match:
        return f"PIPE {compact_match.group(1)} SCH {compact_match.group(2)}"

    return raw


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
        key = f"{nest.profile_family.value.upper()} @ {nest.stock_length_in:.3f} in"
        stock_counter[key] += 1

    ws.append(["Nest Cut List"])
    ws.append(["Date", dt.strftime("%Y-%m-%d")])
    ws.append(["Time", dt.strftime("%H:%M:%S")])
    ws.append(["Total Nests", nest_count])
    ws.append(["Total Pieces", piece_count])
    ws.append(["Raw Stock Summary", "; ".join(f"{k}: {v}" for k, v in sorted(stock_counter.items()))])
    ws.append([])

    ws.append(CUTLIST_COLUMNS)

    for nest in nests:
        nest_filename = f"{nest.nest_id}.cnc"
        ws.append([f"Nest: {nest_filename}"])
        for order, placement in enumerate(nest.placements, start=1):
            drop = max(0.0, nest.stock_length_in - placement.end_in)
            notes = placement.transition_reason
            ws.append(
                [
                    nest_filename,
                    order,
                    placement.part_mark,
                    normalize_material_shape(placement.profile_designation),
                    round(placement.length_in, 3),
                    round(placement.start_offset_in, 3),
                    round(drop, 3),
                    round(placement.transition_trim_before_in, 3),
                    notes,
                    placement.source_file,
                ]
            )
        ws.append([])

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out
