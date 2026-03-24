# STPtoCNC Roadmap

## Phases

1. **Reverse engineering + data model**
   - Refine typed representation of parts/features/nests/program blocks.
   - Parse archived EMI `.CNC` examples into structured JSON for comparison.
2. **EMI writer / post output layer**
   - Emit stable ROP V1.4-style outputs from structured machine operations.
   - Track unknown/assumed semantics with explicit placeholders.
3. **Input importers**
   - Implement NC1 inspection/import path for early geometry extraction.
   - Implement STEP/STP import and round-tube feature extraction.
4. **Nesting engine**
   - Implement multi-part nesting into one 252 in stick.
   - Add configurable chuck loss, scrap, and minimum-gap constraints.
5. **Production hardening**
   - Regression tests using matched source inputs and expected `.CNC` output.
   - Validation on shop-floor sample runs.

## Key risks

- **Geometry extraction uncertainty** from STEP solids is the largest technical risk.
- **Undocumented machine semantics** in legacy posts can cause output mismatch.
- **Sample coverage risk** if archived inputs are not representative.

## Working assumptions

- Target dialect for v1 is **EMI 2400 PROMPTS ROP V1.4**.
- Nominal stock length is **252.0 in** (21 feet).
- Multiple parts may be nested into one stick.
- Source inputs should eventually include both **STEP/STP** and **NC1**.
- Chuck loss, scrap allowances, and minimum gap must remain configurable.

## Next required sample files

1. Archived EMI `.CNC` files that represent accepted ROP V1.4 production outputs.
2. Matched part source files for those programs:
   - STEP/STP examples
   - NC1 examples (if available)
3. Nest metadata, if available:
   - Part order
   - Cut sequence intent
   - Known setup assumptions
