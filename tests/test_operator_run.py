from __future__ import annotations

import json
from pathlib import Path

from stptocnc.workflows.operator_run import run_operator_test_interface


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
