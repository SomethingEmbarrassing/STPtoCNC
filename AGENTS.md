# AGENTS.md

## Project goal
Build a Python toolkit that converts **STP/NC1** inputs into **EMI 2400 ROP V1.4** `.CNC` programs.

## Setup
Run from repository root:

```bash
python -m pip install -e .
```

## CLI quick checks

```bash
stptocnc --help
python -m stptocnc.cli.main --help
```

## GUI launch (operator-primary)

```bash
stptocnc-gui
python -m stptocnc.cli.main launch-gui
```

## Packaging quick checks (Windows)

```bash
python -m pip install -e ".[packaging]"
python packaging/tools/build_exe.py --clean
python packaging/tools/build_installer.py --iscc "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe"
```

## Scope guidance
- Prioritize **round tube / pipe** workflows first for production writer behavior.
- Preserve parser-first support for HSS and angle NC1 records.
- Support configurable stock defaults by profile family (pipe=252 in, hss=240 in, angle=240 in).
- Use NC1 quantity when present, otherwise default quantity to 1 (user-overridable later).
- Output is EMI-specific: **do not target generic G-code**.
- **Do not assume undocumented M-codes**; keep unknown semantics explicit.

## Nesting direction (future UI assumption)
- UI intent is linear stock assignment on a stock bar, not a full 3D viewer.
- Domain should expose stock length, used length, remaining length, and placements for this.
- Automatic nesting should reuse compatible remnants on previously opened sticks before opening new stock.
- Adjacency trim rule:
  - first part on fresh stock gets no trim
  - trim (0.25 in) only when previous end is not compatible with next start
  - unknown end semantics default conservative (trim)

## Development priorities
1. CNC parser
2. CNC writer
3. NC1 importer
4. STP importer
5. nesting engine + linear assignment workflow


## Finalize-time output
- Finalize workflow should emit nested CNC artifacts and an operator cut list `.xlsx`.
- Do not emit blank placeholder nested CNC files.
- If specific machine commands are known from manuals, map them via an EMI profile input rather than hard-coding.
- Cut list is one flat worksheet (`CutList`) with report header + detailed grouped-by-nest rows.
- Do not collapse sequence rows if it loses cut order.
- Normalize material display for operators:
  - HSS -> HSS form
  - Angle -> L form
  - Pipe -> `PIPE <size> SCH <schedule>`
- Preserve PieceMaker table semantics where known (e.g., flat-cut flag behavior and rotational offset parsing).
- Keep backend support for manual piece reassignment between compatible nests for future drag/drop UI.
