# STPtoCNC

STPtoCNC is a Python toolkit for converting tube/pipe part definitions into **EMI 2400** `.CNC` programs aligned to the **EMI 2400 PROMPTS ROP V1.4** family.

## Purpose

This repository is intentionally machine/post specific.
It is **not** a generic CAM or generic G-code project.

## Current focus

- Build parser-first tooling for archived `.CNC` analysis.
- Maintain a clean internal model for part features and machine operations.
- Emit controlled, minimal EMI-style program output for iterative validation.

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

> This project targets EMI-specific `.CNC` output and does not target generic G-code.

## Scope guidance

- Round tube / pipe first.
- Nesting into 21 ft / 252 in sticks is required.
- Keep unknown machine semantics explicit; do not invent undocumented behavior.

## Short roadmap summary

1. Parser / inspection
2. Writer / post
3. NC1 import
4. STP import
5. Nesting engine

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
docs/
tests/
```

## License posture

No permissive open-source license is included at this stage.
