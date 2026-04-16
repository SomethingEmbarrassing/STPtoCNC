from pathlib import Path

from openpyxl import load_workbook

from stptocnc.workflows import finalize_nest_run


def test_finalize_nest_run_creates_cutlist(tmp_path: Path) -> None:
    cutlist = tmp_path / "final-cutlist.xlsx"
    cnc_dir = tmp_path / "cnc"

    result = finalize_nest_run(
        nc1_files=["docs/pp1016.nc1", "docs/as1007.nc1"],
        cutlist_output=cutlist,
        cnc_output_dir=cnc_dir,
    )

    assert result["status"] == "ok"
    assert cutlist.exists()
    assert len(result["cnc_files"]) >= 1
    first_cnc = Path(result["cnc_files"][0])
    cnc_text = first_cnc.read_text(encoding="utf-8")
    assert "(PLACEHOLDER NESTED CNC)" not in cnc_text
    assert "(POST EMI 2400 PROMPTS ROP V1.4)" in cnc_text
    assert "(PIECE " in cnc_text

    wb = load_workbook(cutlist)
    assert wb.sheetnames == ["CutList"]
