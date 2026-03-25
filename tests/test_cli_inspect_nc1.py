import json
import os
import subprocess


def test_cli_inspect_nc1_returns_structured_json() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    result = subprocess.run(
        ["python", "-m", "stptocnc.cli.main", "inspect-nc1", "docs/pp1016.nc1"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] != "placeholder"
    assert payload["status"] == "ok"
    assert "raw_summary" in payload
    assert "distinct_record_prefixes" in payload["raw_summary"]
