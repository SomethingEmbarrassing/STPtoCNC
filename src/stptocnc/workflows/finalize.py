"""Finalize-nest orchestration workflow."""

from __future__ import annotations

from pathlib import Path

from stptocnc.config import NestingDefaults
from stptocnc.importers import parse_nc1_file
from stptocnc.models import expand_part_instances
from stptocnc.models.nesting import LinearNest
from stptocnc.nesting import pack_instances_first_fit
from stptocnc.post.emi_writer import emit_nested_nest_to_emi
from stptocnc.reports import write_cutlist_workbook


def _emit_nested_cnc(nest: LinearNest, output_dir: Path) -> Path:
    """Emit nest-aware EMI-oriented CNC artifact."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{nest.nest_id}.cnc"
    path.write_text(emit_nested_nest_to_emi(nest), encoding="utf-8")
    return path


def finalize_nest_run(
    nc1_files: list[str | Path],
    cutlist_output: str | Path,
    cnc_output_dir: str | Path | None = None,
    defaults: NestingDefaults | None = None,
    quantity_overrides: dict[str, int] | None = None,
) -> dict[str, object]:
    """Finalize a nest run by producing nested artifacts and operator cut list."""
    cfg = defaults or NestingDefaults()

    parts = [parse_nc1_file(path) for path in nc1_files]
    instances = expand_part_instances(parts, quantity_overrides=quantity_overrides)
    nesting_result = pack_instances_first_fit(instances, cfg)

    cnc_paths: list[str] = []
    if cnc_output_dir is not None:
        out_dir = Path(cnc_output_dir)
        for nest in nesting_result.nests:
            cnc_paths.append(str(_emit_nested_cnc(nest, out_dir)))

    cutlist_path = write_cutlist_workbook(nesting_result.nests, cutlist_output)

    return {
        "status": "ok",
        "nests": len(nesting_result.nests),
        "pieces": sum(len(n.placements) for n in nesting_result.nests),
        "cutlist": str(cutlist_path),
        "cnc_files": cnc_paths,
    }
