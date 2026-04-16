"""Operator-facing test-run workflow and report rendering."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path

from stptocnc.config import NestingDefaults
from stptocnc.importers import parse_nc1_file
from stptocnc.models import expand_part_instances
from stptocnc.nesting import pack_instances_first_fit
from stptocnc.workflows.finalize import finalize_nest_run


def parse_quantity_overrides(tokens: list[str] | None) -> dict[str, int]:
    """Parse PART=QTY tokens into a validated quantity override mapping."""
    overrides: dict[str, int] = {}
    for raw in tokens or []:
        token = raw.strip()
        if not token:
            continue
        if "=" not in token:
            raise ValueError(f"Invalid quantity override '{token}'. Use PART=QTY.")
        part_mark, qty_text = token.split("=", 1)
        mark = part_mark.strip()
        if not mark:
            raise ValueError("Invalid quantity override with empty part mark.")
        qty = int(qty_text.strip())
        if qty < 1:
            raise ValueError(f"Quantity override for '{mark}' must be >= 1.")
        overrides[mark] = qty
    return overrides


def discover_nc1_files(path: str | Path, recursive: bool = True) -> list[Path]:
    """Resolve NC1 inputs from either a file path or directory path."""
    root = Path(path)
    if root.is_file():
        return [root]
    if not root.exists():
        raise FileNotFoundError(f"Input path does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"Input path must be an NC1 file or directory: {root}")

    pattern = "**/*.nc1" if recursive else "*.nc1"
    files = sorted(root.glob(pattern))
    files.extend(sorted(root.glob("**/*.NC1") if recursive else root.glob("*.NC1")))

    deduped: list[Path] = []
    seen: set[Path] = set()
    for file in files:
        resolved = file.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(file)

    if not deduped:
        raise ValueError(f"No NC1 files found under: {root}")
    return deduped


def _render_operator_html(
    *,
    source_path: Path,
    generated_at_utc: str,
    nc1_files: list[Path],
    parts: list[object],
    nests: list[object],
    cutlist_path: Path,
    cnc_dir: Path | None,
) -> str:
    file_rows = "\n".join(f"<li>{escape(str(path))}</li>" for path in nc1_files)
    part_rows = "\n".join(
        "<tr>"
        f"<td>{escape(part.part_mark)}</td>"
        f"<td>{escape(part.profile_family.value)}</td>"
        f"<td>{part.quantity}</td>"
        f"<td>{part.length_in:.3f}</td>"
        f"<td>{escape(part.profile_designation or '')}</td>"
        f"<td>{escape(part.material or '')}</td>"
        f"<td>{escape(path.name if (path := Path(part.source_path or '')) else '')}</td>"
        "</tr>"
        for part in parts
    )

    nest_cards: list[str] = []
    for nest in nests:
        placement_rows = "\n".join(
            "<tr>"
            f"<td>{i}</td>"
            f"<td>{escape(placement.part_mark)}</td>"
            f"<td>{placement.length_in:.3f}</td>"
            f"<td>{placement.offset_in:.3f}</td>"
            f"<td>{placement.transition_trim_before_in:.3f}</td>"
            f"<td>{escape(placement.transition_reason)}</td>"
            "</tr>"
            for i, placement in enumerate(nest.placements, start=1)
        )
        bar_pct = min(100.0, nest.utilization_ratio * 100.0)
        nest_cards.append(
            "<section class='card'>"
            f"<h3>{escape(nest.nest_id)} — {escape(nest.profile_family.value.upper())}</h3>"
            f"<p>Stock {nest.stock_length_in:.3f} in | Used {nest.used_length_in:.3f} in | Remaining {nest.remaining_length_in:.3f} in</p>"
            "<div class='bar-wrap'><div class='bar' style='width: "
            f"{bar_pct:.2f}%'></div></div>"
            "<table><thead><tr>"
            "<th>Cut Order</th><th>Part Mark</th><th>Length (in)</th>"
            "<th>Start Offset (in)</th><th>Trim Before (in)</th><th>Reason</th>"
            "</tr></thead><tbody>"
            f"{placement_rows}"
            "</tbody></table></section>"
        )

    cnc_display = escape(str(cnc_dir)) if cnc_dir is not None else "(disabled)"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>STPtoCNC Operator Nest View</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; line-height: 1.4; }}
    h1, h2, h3 {{ margin: 0.4rem 0; }}
    .card {{ border: 1px solid #ccc; border-radius: 8px; padding: 12px; margin: 12px 0; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    th, td {{ border: 1px solid #ddd; padding: 6px; text-align: left; font-size: 0.92rem; }}
    th {{ background: #f7f7f7; }}
    .bar-wrap {{ height: 14px; border: 1px solid #ccc; border-radius: 8px; overflow: hidden; width: 100%; max-width: 500px; }}
    .bar {{ height: 100%; background: #2f80ed; }}
    code {{ background: #f1f1f1; padding: 1px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>STPtoCNC Operator Nest View</h1>
  <p><strong>Generated (UTC):</strong> {escape(generated_at_utc)}</p>
  <p><strong>Input root:</strong> <code>{escape(str(source_path))}</code></p>
  <p><strong>Cut list:</strong> <code>{escape(str(cutlist_path))}</code></p>
  <p><strong>CNC output dir:</strong> <code>{cnc_display}</code></p>
  <h2>Loaded NC1 files ({len(nc1_files)})</h2>
  <ul>{file_rows}</ul>

  <h2>Parts available to the operator ({len(parts)})</h2>
  <table>
    <thead>
      <tr><th>Part Mark</th><th>Family</th><th>Qty</th><th>Length (in)</th><th>Profile</th><th>Material</th><th>Source</th></tr>
    </thead>
    <tbody>{part_rows}</tbody>
  </table>

  <h2>Suggested linear nests ({len(nests)})</h2>
  {"".join(nest_cards)}

  <h2>Operator notes</h2>
  <ul>
    <li>Use this as a linear stick-assignment aid during test runs.</li>
    <li>Cut order rows are intentionally preserved and not collapsed.</li>
    <li>Unknown end semantics stay conservative with trim insertion logic.</li>
  </ul>
</body>
</html>
"""


def run_operator_test_interface(
    *,
    input_path: str | Path,
    output_dir: str | Path,
    recursive: bool = True,
    emit_cnc: bool = True,
    defaults: NestingDefaults | None = None,
    quantity_overrides: dict[str, int] | None = None,
) -> dict[str, object]:
    """Build artifacts for an operator-visible test run."""
    root = Path(input_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    nc1_files = discover_nc1_files(root, recursive=recursive)
    file_strings = [str(path) for path in nc1_files]

    cutlist_path = out_dir / "cutlist.xlsx"
    cnc_dir = out_dir / "cnc" if emit_cnc else None
    finalize_result = finalize_nest_run(
        file_strings,
        cutlist_path,
        cnc_output_dir=cnc_dir,
        defaults=defaults,
        quantity_overrides=quantity_overrides,
    )

    parts = [parse_nc1_file(path) for path in nc1_files]
    nests = pack_instances_first_fit(
        expand_part_instances(parts, quantity_overrides=quantity_overrides),
        defaults=defaults,
    ).nests
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    html_path = out_dir / "operator_nest_view.html"
    html_path.write_text(
        _render_operator_html(
            source_path=root,
            generated_at_utc=generated_at,
            nc1_files=nc1_files,
            parts=parts,
            nests=nests,
            cutlist_path=cutlist_path,
            cnc_dir=cnc_dir,
        ),
        encoding="utf-8",
    )

    summary = {
        "status": "ok",
        "generated_at_utc": generated_at,
        "input_path": str(root),
        "files_loaded": len(nc1_files),
        "nests": finalize_result["nests"],
        "pieces": finalize_result["pieces"],
        "cutlist": str(cutlist_path),
        "cnc_files": finalize_result["cnc_files"],
        "operator_view": str(html_path),
    }
    (out_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "nests_snapshot.json").write_text(
        json.dumps(
            {
                "nests": [
                    {
                        "nest_id": nest.nest_id,
                        "profile_family": nest.profile_family.value,
                        "stock_length_in": nest.stock_length_in,
                        "used_length_in": nest.used_length_in,
                        "remaining_length_in": nest.remaining_length_in,
                        "placements": [asdict(p) for p in nest.placements],
                    }
                    for nest in nests
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return summary
