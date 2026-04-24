import json
import os
import subprocess
from pathlib import Path


def test_cli_check_conformance_returns_nonzero_for_mismatch(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.cnc"
    generated = tmp_path / "generated.cnc"
    accepted.write_text("%\n(PROGRAM A)\n(POST EMI)\nG90\nM15\nM30\n%\n", encoding="utf-8")
    generated.write_text("%\n(PROGRAM B)\n(POST EMI)\nG90\nM30\n%\n", encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    result = subprocess.run(
        ["python", "-m", "stptocnc.cli.main", "check-conformance", str(generated), str(accepted)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "needs_review"

