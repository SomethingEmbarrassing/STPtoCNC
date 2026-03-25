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

## Scope guidance
- Prioritize **round tube / pipe** workflows first for production writer behavior.
- Preserve parser-first support for HSS and angle NC1 records.
- Support configurable stock defaults by profile family (pipe=252 in, hss=240 in, angle=240 in).
- Use NC1 quantity when present, otherwise default quantity to 1 (user-overridable later).
- Output is EMI-specific: **do not target generic G-code**.
- **Do not assume undocumented M-codes**; keep unknown semantics explicit.

## Nesting direction (future UI assumption)
- UI intent is linear stock assignment (drag/drop on a stick bar), not a full 3D viewer.
- Domain should expose stock length, used length, remaining length, and placements for this.

## Development priorities
1. CNC parser
2. CNC writer
3. NC1 importer
4. STP importer
5. nesting engine + linear assignment workflow
