import json
import os
import subprocess
from pathlib import Path


def test_cli_operator_run_creates_operator_artifacts(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    out_dir = tmp_path / "operator"

    result = subprocess.run(
        [
            "python",
            "-m",
            "stptocnc.cli.main",
            "operator-run",
            "docs/pp1016.nc1",
            "--output-dir",
            str(out_dir),
            "--qty",
            "pp1016=3",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["pieces"] == 3
    assert (out_dir / "operator_nest_view.html").exists()
