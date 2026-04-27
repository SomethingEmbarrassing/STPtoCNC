# STPtoCNC

STPtoCNC is a Python toolkit for converting tube/pipe and profile-part definitions into **EMI 2400** `.CNC` programs aligned to the **EMI 2400 PROMPTS ROP V1.4** family.

## Purpose

This repository is intentionally machine/post specific.
It is **not** a generic CAM or generic G-code project.

## Current focus

- Build parser-first tooling for archived `.CNC` and `.nc1` analysis.
- Maintain a clean internal model for part features and machine operations.
- Emit controlled, minimal EMI-style program output for iterative validation.
- Inspect PIPE/HSS/ANGLE NC1 records (including BO/KO when present) without guessing undocumented semantics.
- Prepare NC1-driven linear nesting foundations (stock defaults, quantity expansion, and placement math).

## Installation & Launch (Windows-first)

From the repository root:

```bash
python -m pip install -e .
```

Windows `py` launcher equivalent:

```bash
py -m pip install -e .
```

### Operator GUI (primary workflow)

Launch with installed script:

```bash
stptocnc-gui
```

Or launch via module:

```bash
python -m stptocnc.cli.main launch-gui
```

Windows `py` launcher variant:

```bash
py -m stptocnc.cli.main launch-gui
```

Batch shortcut:

```bat
scripts\launch_stptocnc_gui.bat
```

The desktop GUI supports:
- selecting one or more NC1 files
- editing stock defaults (pipe/hss/angle)
- optional quantity overrides (`PART=QTY,PART2=QTY`)
- linear nest preview (parts, trim cuts, drop)
- finalize/export of nested CNC and cut list outputs

### Packaged Windows `.exe` build (PyInstaller)

Install packaging dependency:

```bash
python -m pip install -e ".[packaging]"
```

Build executable:

```bash
python packaging/tools/build_exe.py --clean
```

Build artifacts:
- `dist/STPtoCNC/STPtoCNC.exe` (double-click launch)
- `build/` intermediate files

### Windows installer build (Inno Setup)

1. Install Inno Setup 6 on Windows.
2. Build the executable first (section above).
3. Build installer:

```bash
python packaging/tools/build_installer.py --iscc "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

Installer artifact:
- `dist/installer/STPtoCNC-Setup.exe`

Operator path (packaged flow):
1. Run `STPtoCNC-Setup.exe`
2. Launch from Start Menu/Desktop shortcut
3. Browse NC1 files
4. Preview nests
5. Finalize to export nested `.CNC` and cut list `.xlsx`

### CLI/backend (development + automation)

Run CLI checks:

```bash
stptocnc --help
python -m stptocnc.cli.main --help
```

If tests fail during collection with `ModuleNotFoundError: No module named 'openpyxl'`,
re-run the editable install command above to install runtime dependencies from
`pyproject.toml`.

NC1 conversion command:

```bash
stptocnc convert-nc1 path/to/input.nc1 path/to/output.cnc
```

Finalize run (nested artifacts + operator cut list):

```bash
stptocnc finalize-nest docs/pp1007.nc1 docs/pp1016.nc1 --cutlist out/cutlist.xlsx --cnc-dir out/cnc
```

Finalize run with explicit per-piece-mark quantity overrides:

```bash
stptocnc finalize-nest docs/pp1007.nc1 docs/pp1016.nc1 --cutlist out/cutlist.xlsx --cnc-dir out/cnc --qty pp1007=2 --qty pp1016=4
```

Finalize run using machine-profile overrides (recommended when mapping commands from PieceMaker documentation):

```bash
stptocnc finalize-nest docs/pp1007.nc1 docs/pp1016.nc1 --cutlist out/cutlist.xlsx --cnc-dir out/cnc --emi-profile docs/emi_machine_profile.sample.json
```

Operator batch interface (loads NC1 files, creates suggested linear nests, and writes an HTML operator view):

```bash
stptocnc operator-run docs --output-dir out/operator-run
```

Operator batch interface with per-piece-mark quantity overrides:

```bash
stptocnc operator-run docs --output-dir out/operator-run --qty pp1016=3 --qty as1007=1
```

Outputs are written to `out/operator-run/`:
- `operator_nest_view.html` (operator-facing interface)
- `cutlist_YYYYMMDD_HHMMSS.xlsx` (CutList worksheet for shop use)
- `nests_snapshot.json` (detailed ordered placement snapshot)
- `run_summary.json` (run metadata)
- `cnc/` (nested CNC artifacts)

Inspection commands (structured JSON):

```bash
stptocnc inspect-nc1 docs/pp1016.nc1
stptocnc inspect-cnc docs/pp1016-QC.cnc
stptocnc check-conformance out/cnc/nest-1.cnc docs/pp1016-QC.cnc
stptocnc calibrate-reference docs/as1007.nc1 "docs/as1007 25-41-QC.cnc" --output-dir out/calibration
```

Reference-calibration sample commands that match files currently tracked in `docs/`:

```bash
stptocnc calibrate-reference docs/as1019.nc1 "docs/as1019 25-41-QC.cnc" --output-dir out/as1019-calibration
stptocnc calibrate-reference docs/h1001.nc1 docs/h1001-QC.cnc --output-dir out/h1001-calibration
stptocnc calibrate-reference docs/pp1016.nc1 docs/pp1016-QC.cnc --output-dir out/pp1016-calibration
```

If you receive `No such file or directory`, verify exact filenames in `docs/` first:

```bash
find docs -maxdepth 1 -type f
```

## NC1-driven nesting assumptions (current)

- Multiple NC1 inputs should eventually produce **one nested `.CNC` per stock stick**.
- Stock-length defaults are profile-family based (configurable):
  - Pipe: `252.0 in` (21')
  - HSS: `240.0 in` (20')
  - Angle: `240.0 in` (20')
- NC1 quantity is used when present; otherwise default quantity is `1`.
- Nest visualization target is **linear** (stock bar / cut strip), not 3D solids.
- Nesting reuses compatible open-stick remnants/drops using a deterministic best-fit reuse heuristic.
- Adjacency trim inference (current helper):
  - First part on a fresh stick gets **no leading trim** (fresh raw stock is flat).
  - Between adjacent parts, trim is added **only when previous end is not flat-compatible for next start**.
  - Trim value, when needed, is fixed at `0.25 in` into fresh raw stock.
  - Unknown end semantics default conservative (trim inserted).
  - TODO: wire this to robust NC1-derived end-feature classification.


## Operator cut list export (single-sheet XLSX)

When a nest run is finalized, the framework exports one workbook with one sheet (`CutList`) containing:
- top report header: title, date, time, total nests, total pieces, grouped stock summary
- detailed rows grouped by nest, preserving cut order
- required operator columns:
  - Nest ID (nest filename)
  - Cut Order
  - Piece Mark
  - Material Shape (normalized)
  - Piece Length
  - Start Offset
  - Drop
  - Trim Cut

Material display normalization rules:
- HSS: stays in HSS form
- Angle: stays in L form
- Pipe: displayed as `PIPE <size> SCH <schedule>`

Current assumptions:
- one row per placed part instance (no quantity collapsing)
- trim-before-piece comes from adjacency inference
- start offset defaults to 0.0 until richer start-feature offsets are available
- manual reassignment framework is available in backend (`move_instance_between_nests`) for future drag/drop UI wiring

> This project targets EMI-specific `.CNC` output and does not target generic G-code.

## Nested CNC output status

`finalize-nest` and GUI finalize now emit nest-aware EMI-oriented files with:
- explicit EMI program header/footer structure
- per-piece sequencing in nest cut order
- trim-before-piece annotations
- per-piece end-loop cut blocks derived from parsed NC1 values

Unknown machine semantics are left explicit in output comments (not blank placeholders),
including trim-cut machine code mapping details that require shop-specific EMI examples.

## PieceMaker manual alignment (recommended)

Use an EMI machine profile JSON to encode command mappings discovered from shop documentation:
- sample file: `docs/emi_machine_profile.sample.json`
- currently configurable: post label, trim cut command, torch on/off commands, torch raise command, piece completion prompt, nest completion prompt, footer command

When `trim_cut_command` is unset, finalize output will include an explicit note:
`(TRIM CUT COMMAND NOT CONFIGURED)` so missing semantics are visible during testing.

Detailed alignment checklist: `docs/piecemaker_manual_alignment.md`.

Current implemented PieceMaker table-aligned fields:
- `END-1 FLAT` / `END-2 FLAT` parsing (`Y`/`N`)
- `ROTATIONAL OFFSET` parsing
- flat-cut behavior: joining diameter forced to `200.0` when flat is checked
- manual-derived command defaults: `M15` torch on, `M16` torch off, `M25` torch raise

## Future packaging

The GUI entry point is isolated as `stptocnc.gui_entry:main`, and packaging assets live under:
- `packaging/pyinstaller/stptocnc_gui.spec`
- `packaging/inno/stptocnc_installer.iss`
- `packaging/tools/build_exe.py`
- `packaging/tools/build_installer.py`

Future production release path:
- add code-signing for `.exe` and installer
- finalize icon/branding resources
- validate with accepted shop EMI reference nests before wider rollout

## Scope guidance

- Round tube / pipe first for production output.
- HSS and angle are currently inspection/parser-first.
- Nesting into configurable stock sticks is required.
- Keep unknown machine semantics explicit; do not invent undocumented behavior.

## Short roadmap summary

1. Parser / inspection
2. Writer / post
3. NC1 import
4. STP import
5. Nesting engine + linear operator assignment UI support

## Repository layout

```text
README.md
AGENTS.md
pyproject.toml
src/stptocnc/
  models/
  parsers/
  importers/
  post/
  nesting/
  cli/
  config/
docs/
tests/
```

## License posture

No permissive open-source license is included at this stage.
