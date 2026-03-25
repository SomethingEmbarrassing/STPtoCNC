# STPtoCNC Roadmap

## Target output

- **EMI 2400 PROMPTS ROP V1.4** `.CNC`
- NC1-driven workflow to one nested `.CNC` output per stock stick

## Phases

1. Parser / inspection
2. Writer / post
3. NC1 import normalization (quantity + profile families)
4. STP import
5. Nesting and linear operator assignment workflow
6. Finalize-time operator cut list export (single-sheet `.xlsx`)

## Current nesting assumptions

- Stock defaults by profile family (editable):
  - Pipe: **252.0 in**
  - HSS: **240.0 in**
  - Angle: **240.0 in**
- NC1 quantity should be respected when present; fallback is quantity=1.
- Part instances are expanded from quantity before nesting placement.
- Nesting UI target is a linear bar/strip layout, not a 3D model viewer.
- Adjacency trim rule helper (current):
  - first part on fresh stick: no trim
  - between adjacent parts: +0.25 in only when previous end is not flat-compatible for next start
  - unknown end semantics default conservative (trim)
  - TODO: replace placeholder end-condition detection with real feature-derived logic.

## Major risks

- Feature extraction quality from STP solids.
- Undocumented EMI semantics in legacy programs/posts.
- Need for matched sample sets to validate translation quality.

## Next required sample files

- Multi-part NC1 set meant to share one stock stick.
- Matching accepted nested EMI `.CNC` output for that stick.
- Additional non-round examples with known BO/KO/SI intent annotations.


## Finalize-time reporting assumptions

- On finalize, generate one flat worksheet (`CutList`) for the run.
- Header area includes date/time, stock summary, total pieces, total nests.
- Detailed rows grouped by nest and preserved cut order.
- Columns include: Nest ID, Cut Order, Piece Mark, Material Shape, Piece Length, Start Offset, Drop, Trim Cut.
- Material display normalized for operators (HSS, L, PIPE size+sched).
