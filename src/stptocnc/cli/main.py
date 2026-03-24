"""CLI entry point for STPtoCNC."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from stptocnc.parsers.cnc_inspector import inspect_cnc_file
from stptocnc.post.emi_writer import emit_minimal_sample


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stptocnc", description="STP/NC1 to EMI .CNC tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_cnc = sub.add_parser("inspect-cnc", help="Inspect a .CNC file and print JSON analysis")
    inspect_cnc.add_argument("path", type=Path, help="Path to CNC file")

    emit_sample = sub.add_parser("emit-sample-cnc", help="Emit a minimal synthetic EMI .CNC sample")
    emit_sample.add_argument("--program-id", default="SAMPLE001", help="Program id to embed in sample")

    inspect_step = sub.add_parser("inspect-step", help="Placeholder STEP inspection command")
    inspect_step.add_argument("path", type=Path, help="Path to STEP/STP file")

    inspect_nc1 = sub.add_parser("inspect-nc1", help="Placeholder NC1 inspection command")
    inspect_nc1.add_argument("path", type=Path, help="Path to NC1 file")

    return parser


def main() -> int:
    """Run CLI and dispatch commands."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "inspect-cnc":
        result = inspect_cnc_file(args.path)
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "emit-sample-cnc":
        print(emit_minimal_sample(program_id=args.program_id), end="")
        return 0

    if args.command == "inspect-step":
        print(
            json.dumps(
                {
                    "path": str(args.path),
                    "status": "placeholder",
                    "message": "STEP inspection is not implemented yet.",
                },
                indent=2,
            )
        )
        return 0

    if args.command == "inspect-nc1":
        print(
            json.dumps(
                {
                    "path": str(args.path),
                    "status": "placeholder",
                    "message": "NC1 inspection is not implemented yet.",
                },
                indent=2,
            )
        )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
