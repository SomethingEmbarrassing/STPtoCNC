"""Build STPtoCNC Windows GUI executable via PyInstaller."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Build STPtoCNC GUI executable with PyInstaller")
    parser.add_argument("--clean", action="store_true", help="Run PyInstaller with --clean")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    spec = root / "packaging" / "pyinstaller" / "stptocnc_gui.spec"
    if not spec.exists():
        raise FileNotFoundError(f"Missing spec file: {spec}")

    cmd = [sys.executable, "-m", "PyInstaller", str(spec), "--noconfirm"]
    if args.clean:
        cmd.append("--clean")

    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=root)


if __name__ == "__main__":
    raise SystemExit(main())
