# PieceMaker Manual v5.2.5 alignment notes

## Repository status

At implementation time, `PieceMaker Manual v5.2.5.PDF` was not present in this repository tree,
so command-level mappings were implemented through a configurable machine-profile layer rather
than hard-coded assumptions.

## Implemented recommendation

Use `docs/emi_machine_profile.sample.json` and `--emi-profile` at finalize time to map
manual-confirmed commands without changing Python source code.

Current configurable fields:
- `post_label`
- `trim_cut_command`
- `piece_complete_prompt`
- `nested_complete_prompt`
- `footer_command`

## Immediate follow-up once manual PDF is added

1. Copy exact trim/separator/chuck/autoload commands from manual into profile.
2. Validate one accepted production nest output against emitted CNC.
3. Lock profile into a shop-specific release config for installer builds.
