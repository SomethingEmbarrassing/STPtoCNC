"""Calibration workflow for NC1 + legacy CNC behavioral comparison."""

from __future__ import annotations

import json
from pathlib import Path

from stptocnc.importers import parse_nc1_file
from stptocnc.post.emi_writer import emit_nc1_part_to_emi


def _behavior_flags(cnc_text: str) -> dict[str, bool]:
    lines = cnc_text.splitlines()
    joined = "\n".join(lines)
    return {
        "setup_style": all(token in joined for token in ["G20", "G58", "T1", "G43 H1", "#29001", "#29002"]),
        "torch_timing": "M15" in joined and "M16" in joined and "M16\n;End1->End2 Reposition" in joined,
        "pierce_toe": "G01 X-0.0010 F#29001" in joined and "G01 X0.0002 F#29001" in joined,
        "wrapped_modal": "G01 G93.1 F#29002" in joined and "G94" in joined and "G91" in joined,
        "end_sequence": ";End1 - Start" in joined and ";End2 - Start" in joined and ";End1->End2 Reposition" in joined,
    }


def build_calibration_report(
    nc1_path: str | Path,
    legacy_cnc_path: str | Path,
    output_dir: str | Path,
) -> dict[str, object]:
    """Generate calibration bundle: parsed NC1 model + generated CNC + behavior diff."""
    nc1 = Path(nc1_path)
    legacy = Path(legacy_cnc_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    part = parse_nc1_file(nc1)
    generated_cnc = emit_nc1_part_to_emi(part)
    generated_path = out_dir / f"{part.part_mark}-generated.cnc"
    generated_path.write_text(generated_cnc, encoding="utf-8")

    legacy_text = legacy.read_text(encoding="utf-8")
    generated_flags = _behavior_flags(generated_cnc)
    legacy_flags = _behavior_flags(legacy_text)

    report = {
        "status": "ok",
        "nc1_path": str(nc1),
        "legacy_cnc_path": str(legacy),
        "generated_cnc_path": str(generated_path),
        "nc1_summary": {
            "part_mark": part.part_mark,
            "material": part.material,
            "profile": part.profile_designation,
            "quantity": part.quantity,
            "quantity_source": part.quantity_source,
            "length_in": part.length_in,
            "rotational_offset_deg": part.rotational_offset_deg,
            "ak_rows_present": bool(part.ak_rows),
            "ak_rows_count": len(part.ak_rows or []),
            "ak_rows_sample": (part.ak_rows or [])[:5],
        },
        "field_to_output_mapping": {
            "stock_profile_data": ["profile_designation", "outer_diameter_in", "wall_thickness_in"],
            "piece_length": "length_in",
            "end1_path": ["end1.angle_deg", "end1.join_diameter_in", "end1.flat_cut"],
            "end2_path": ["end2.angle_deg", "end2.join_diameter_in", "end2.flat_cut"],
            "rotational_offset": "rotational_offset_deg",
            "ak_usage_status": "parsed_and_preserved_not_yet_directly_used_for_path_generation",
            "ak_usage_todo": "TODO: map AK contour rows to wrapped toolpath points when machine mapping is confirmed.",
        },
        "behavior_compare": {
            "generated": generated_flags,
            "legacy": legacy_flags,
            "matches": {k: generated_flags[k] == legacy_flags[k] for k in generated_flags},
        },
        "remaining_geometry_gaps": [
            "AK contour rows are preserved but not yet mapped directly into wrapped path points.",
            "Current cope/miter math is an approximation and may require AK-driven calibration per profile family.",
            "Pierce/toe defaults are profile-configurable but may require machine-specific offsets from shop validation.",
        ],
    }
    report_path = out_dir / "calibration_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
