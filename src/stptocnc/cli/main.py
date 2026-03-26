"""CLI entry point for STPtoCNC."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from stptocnc.importers import parse_nc1_file
from stptocnc.parsers import inspect_cnc_file, inspect_nc1_file
from stptocnc.post.emi_writer import emit_minimal_sample, emit_nc1_part_to_emi
from stptocnc.workflows import finalize_nest_run, run_operator_test_interface


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stptocnc", description="STP/NC1 to EMI .CNC tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_cnc = sub.add_parser("inspect-cnc", help="Inspect a .CNC file and print structured JSON")
    inspect_cnc.add_argument("path", type=Path, help="Path to CNC file")

    emit_sample = sub.add_parser("emit-sample-cnc", help="Emit a minimal synthetic EMI .CNC sample")
    emit_sample.add_argument("--program-id", default="SAMPLE001", help="Program id to embed in sample")

    inspect_step = sub.add_parser("inspect-step", help="Placeholder STEP inspection command")
    inspect_step.add_argument("path", type=Path, help="Path to STEP/STP file")

    inspect_nc1 = sub.add_parser("inspect-nc1", help="Inspect an NC1 file and print structured JSON")
    inspect_nc1.add_argument("path", type=Path, help="Path to NC1 file")

    convert_nc1 = sub.add_parser("convert-nc1", help="Convert NC1 input into a placeholder EMI .CNC output")
    convert_nc1.add_argument("input", type=Path, help="Path to NC1 file")
    convert_nc1.add_argument("output", type=Path, help="Path to output CNC file")

    finalize = sub.add_parser("finalize-nest", help="Finalize a nest run and export cut list workbook")
    finalize.add_argument("inputs", nargs="+", type=Path, help="NC1 input files")
    finalize.add_argument("--cutlist", required=True, type=Path, help="Output .xlsx cut list path")
    finalize.add_argument("--cnc-dir", type=Path, help="Optional output directory for placeholder nested CNC files")

    operator_run = sub.add_parser(
        "operator-run",
        help="Build operator-facing test-run outputs (HTML view, cut list, summary JSON, optional CNC files)",
    )
    operator_run.add_argument("input_path", type=Path, help="Path to NC1 file or directory containing NC1 files")
    operator_run.add_argument("--output-dir", required=True, type=Path, help="Output directory for generated artifacts")
    operator_run.add_argument("--no-recursive", action="store_true", help="Only scan top-level directory for NC1 files")
    operator_run.add_argument("--no-cnc", action="store_true", help="Disable placeholder nested CNC output files")

    sub.add_parser("launch-gui", help="Launch desktop operator GUI (Windows-focused Tkinter app)")

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
        result = inspect_nc1_file(args.path)
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "convert-nc1":
        part = parse_nc1_file(args.input)
        output = emit_nc1_part_to_emi(part)
        args.output.write_text(output, encoding="utf-8")
        print(json.dumps({"status": "ok", "input": str(args.input), "output": str(args.output)}, indent=2))
        return 0

    if args.command == "finalize-nest":
        result = finalize_nest_run(
            nc1_files=[str(path) for path in args.inputs],
            cutlist_output=args.cutlist,
            cnc_output_dir=args.cnc_dir,
        )
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "operator-run":
        result = run_operator_test_interface(
            input_path=args.input_path,
            output_dir=args.output_dir,
            recursive=not args.no_recursive,
            emit_cnc=not args.no_cnc,
        )
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "launch-gui":
        from stptocnc.gui import launch_gui

        launch_gui()
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
