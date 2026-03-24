# STPtoCNC Roadmap

## Target output

- **EMI 2400 PROMPTS ROP V1.4** `.CNC`

## Phases

1. Parser / inspection
2. Writer / post
3. NC1 import
4. STP import
5. Nesting

## Major risks

- Feature extraction quality from STP solids.
- Undocumented EMI semantics in legacy programs/posts.
- Need for matched sample sets to validate translation quality.

## Next required sample files

- Simple NC1 input sample.
- Matching simple EMI `.CNC` output sample.
- Later: matching STP sample for the same part family.
