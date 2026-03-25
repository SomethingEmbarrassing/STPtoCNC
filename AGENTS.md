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
- Prioritize **round tube / pipe** workflows first.
- Support nesting into **21 ft / 252 in** stock sticks.
- Output is EMI-specific: **do not target generic G-code**.
- **Do not assume undocumented M-codes**; keep unknown semantics explicit.

## Development priorities
1. CNC parser
2. CNC writer
3. NC1 importer
4. STP importer
5. nesting engine
