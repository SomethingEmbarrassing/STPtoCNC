import os
import subprocess


def test_cli_convert_help_no_longer_mentions_placeholder() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    result = subprocess.run(
        ["python", "-m", "stptocnc.cli.main", "--help"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    convert_line = next((line for line in result.stdout.splitlines() if "convert-nc1" in line), "")
    assert convert_line
    assert "placeholder" not in convert_line.lower()


def test_cli_operator_run_help_no_longer_mentions_placeholder() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    result = subprocess.run(
        ["python", "-m", "stptocnc.cli.main", "operator-run", "--help"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    assert "placeholder" not in result.stdout.lower()
    assert "Disable nested CNC output files" in result.stdout


def test_cli_inspect_step_reports_not_implemented_status() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    result = subprocess.run(
        ["python", "-m", "stptocnc.cli.main", "inspect-step", "docs/pp1016.nc1"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    assert '"status": "not_implemented"' in result.stdout
