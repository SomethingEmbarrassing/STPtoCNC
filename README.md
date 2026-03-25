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

## Development Setup

From the repository root:

```bash
python -m pip install -e .
```

Run CLI checks:

```bash
stptocnc --help
python -m stptocnc.cli.main --help
```

NC1 conversion command:

```bash
stptocnc convert-nc1 path/to/input.nc1 path/to/output.cnc
```

Inspection commands (structured JSON):

```bash
stptocnc inspect-nc1 docs/pp1016.nc1
stptocnc inspect-cnc docs/pp1016-QC.cnc
```

## NC1-driven nesting assumptions (current)

- Multiple NC1 inputs should eventually produce **one nested `.CNC` per stock stick**.
- Stock-length defaults are profile-family based (configurable):
  - Pipe: `252.0 in` (21')
  - HSS: `240.0 in` (20')
  - Angle: `240.0 in` (20')
- NC1 quantity is used when present; otherwise default quantity is `1`.
- Nest visualization target is **linear** (stock bar / cut strip), not 3D solids.
- Adjacency trim inference (current helper):
  - First part on a fresh stick gets **no leading trim** (fresh raw stock is flat).
  - Between adjacent parts, trim is added **only when previous end is not flat-compatible for next start**.
  - Trim value, when needed, is fixed at `0.25 in` into fresh raw stock.
  - Unknown end semantics default conservative (trim inserted).
  - TODO: wire this to robust NC1-derived end-feature classification.

> This project targets EMI-specific `.CNC` output and does not target generic G-code.

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
