# PieceMaker Manual v5.2.5 alignment notes

## Repository status

Partial manual guidance was provided from page 20/27 (table + notes image). The implementation
below aligns to that information and keeps remaining fields configurable.
Manual pages 16-20 were also reviewed for M-code semantics.

## Implemented recommendation

Use `docs/emi_machine_profile.sample.json` and `--emi-profile` at finalize time to map
manual-confirmed commands without changing Python source code.

Current configurable fields:
- `post_label`
- `trim_cut_command`
- `torch_on_command` (manual: M15)
- `torch_off_command` (manual: M16)
- `torch_raise_command` (manual: M25)
- `piece_complete_prompt`
- `nested_complete_prompt`
- `footer_command`

## Implemented from provided page-20 notes

1. Added parser support for:
   - `END-1 FLAT` and `END-2 FLAT` (Y/N)
   - `ROTATIONAL OFFSET`
2. Applied manual note behavior:
   - if flat cut is checked, joining diameter is set to `200.0` and treated as deactivated
3. Propagated these values into nest placements and nested CNC output comments:
   - `(END1 FLAT: Y|N)`
   - `(END2 FLAT: Y|N)`
   - `(ROTATIONAL OFFSET: <value>)`
4. Added manual-derived default command mapping in machine profile:
   - torch on/off (`M15`/`M16`)
   - torch raise (`M25`)

## Immediate follow-up once manual PDF is added

1. Copy exact trim/separator/chuck/autoload commands from manual into profile.
2. Validate one accepted production nest output against emitted CNC.
3. Lock profile into a shop-specific release config for installer builds.
4. Confirm whether rotational offset should be emitted as a real machine command (instead of a comment).
