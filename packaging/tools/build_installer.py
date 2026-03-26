"""Build STPtoCNC Windows installer via Inno Setup."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess


def main() -> int:
    parser = argparse.ArgumentParser(description="Build STPtoCNC installer with Inno Setup")
    parser.add_argument(
        "--iscc",
        default=r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        help="Path to Inno Setup compiler (ISCC.exe)",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    script = root / "packaging" / "inno" / "stptocnc_installer.iss"
    dist_dir = root / "dist" / "STPtoCNC"
    if not dist_dir.exists():
        raise FileNotFoundError(
            f"Missing PyInstaller output at {dist_dir}. Build executable first with packaging/tools/build_exe.py."
        )
    if not script.exists():
        raise FileNotFoundError(f"Missing installer script: {script}")

    cmd = [args.iscc, str(script)]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=root)


if __name__ == "__main__":
    raise SystemExit(main())
