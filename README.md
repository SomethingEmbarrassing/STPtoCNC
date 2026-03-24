# STPtoCNC

STPtoCNC is a Python application for converting tube/pipe part definitions into **EMI 2400** machine `.CNC` programs, with output conventions aligned to the **EMI 2400 PROMPTS ROP V1.4** post family.

## Why this project exists

Our workflow needs reliable program generation for a specific machine and post style used in production. This project is intentionally **EMI-specific** and is **not** a generic CAM or generic G-code generator.

## Primary target

- Output dialect: **EMI 2400 PROMPTS ROP V1.4**
- Initial part family: **round tube / pipe**
- Initial feature scope:
  - Straight cuts
  - Mitered end cuts
  - Fishmouth / saddle / cope end cuts
  - Simple holes (when practical)
- Production constraint: **nesting multiple parts into one 21-foot stick (252.0 in nominal)**

## Current scope (bootstrap phase)

This repository is currently focused on:

- Internal data models for parts, features, nests, and machine programs.
- EMI-oriented program section abstractions (header, setup, cut sequence, prompts, footer).
- CLI scaffolding for inspection and sample program emission.
- `.CNC` reverse-engineering parser utility that emits structured JSON-like output.

## Planned phases

1. **Reverse-engineering / internal data model**
2. **EMI writer/post layer (ROP V1.4 style)**
3. **Developer parser tooling for archived `.CNC` analysis**
4. **Geometry input and feature extraction (STEP/STP first for round tube)**
5. **21' stick nesting workflow**

This ordering is intentional: the biggest risk is geometry/feature extraction, not text emission.

## Architecture direction

The design leaves room for both future import paths:

- `STP -> EMI .CNC`
- `NC1 -> EMI .CNC`

Even though STP is the business goal, NC1 may provide an earlier path for geometry ingestion and validation.

## Development quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
stptocnc --help
```

## CLI commands (initial)

> Run `python -m pip install -e .` from the repo root before using CLI commands.

- `stptocnc inspect-cnc path/to/file.CNC`
- `stptocnc emit-sample-cnc`
- `stptocnc inspect-step path/to/file.stp`
- `stptocnc inspect-nc1 path/to/file.nc1`

## Repository layout

```text
README.md
pyproject.toml
src/stptocnc/
  models/
  parsers/
  importers/
  post/
  nesting/
  cli/
tests/
docs/
```

## License posture

No permissive open-source license is added at this stage.
