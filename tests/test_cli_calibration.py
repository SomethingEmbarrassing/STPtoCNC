import json
import os
import subprocess
from pathlib import Path


def test_cli_calibrate_reference_generates_report(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    result = subprocess.run(
        [
            "python",
            "-m",
            "stptocnc.cli.main",
            "calibrate-reference",
            "docs/as1007.nc1",
            "docs/as1007 25-41-QC.cnc",
            "--output-dir",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert (tmp_path / "calibration_report.json").exists()
