from __future__ import annotations

import json
from pathlib import Path

from stptocnc.workflows.operator_run import run_operator_test_interface
from stptocnc.workflows.operator_run import parse_quantity_overrides


def test_operator_run_generates_interface_outputs(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = run_operator_test_interface(input_path="docs", output_dir=out_dir, recursive=False)

    assert result["status"] == "ok"
    assert result["files_loaded"] >= 1
    assert (out_dir / "cutlist.xlsx").exists()
    assert (out_dir / "operator_nest_view.html").exists()
    assert (out_dir / "run_summary.json").exists()
    assert (out_dir / "nests_snapshot.json").exists()

    summary = json.loads((out_dir / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["operator_view"].endswith("operator_nest_view.html")


def test_parse_quantity_overrides_accepts_part_specific_values() -> None:
    overrides = parse_quantity_overrides(["pp1016=4", "as1007=2"])
    assert overrides == {"pp1016": 4, "as1007": 2}
