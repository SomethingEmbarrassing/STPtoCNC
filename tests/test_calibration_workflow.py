from pathlib import Path

from stptocnc.workflows import build_calibration_report
from stptocnc.importers import parse_nc1_file


def test_nc1_parser_preserves_ak_rows_from_real_sample() -> None:
    part = parse_nc1_file("docs/pp1016.nc1")
    assert part.ak_rows is not None
    assert len(part.ak_rows) > 0


def test_build_calibration_report_writes_bundle(tmp_path: Path) -> None:
    report = build_calibration_report(
        "docs/as1007.nc1",
        "docs/as1007 25-41-QC.cnc",
        tmp_path,
    )
    assert report["status"] == "ok"
    assert report["nc1_summary"]["part_mark"]
    assert (tmp_path / "calibration_report.json").exists()
    assert Path(report["generated_cnc_path"]).exists()
    assert "ak_usage_todo" in report["field_to_output_mapping"]
    assert "per_end_compare" in report
    assert "numeric_deltas" in report
    assert "sequence_compare" in report
    assert "calibration_score" in report
    assert report["calibration_score"]["behavior_total"] >= report["calibration_score"]["behavior_matches"]
    assert isinstance(report["numeric_deltas"]["line_count_delta"], int)
    assert isinstance(report["per_end_compare"]["end1"]["deltas"]["angle_deg"], float)
