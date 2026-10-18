# Chord Lab 0.1.8: held-chord G/V navigation and focus

[中文](GV_FOCUS.cn.md) · [Usage](LEFT_HAND.md)

## Changes

- V emits command 19 (down-left); G emits command 20 (up-right), on press, alongside held chord keys.
- Physical Esc and left Ctrl navigation removed. Standalone left Shift release still toggles Sustain.
- Harmony engine, parameter ordering, CLAP ID, sounds and MIDI routing unchanged.
- Focus root cause was Sway focus-follows-mouse, not mouseExit or a button defect.
  Reproduced with native Wayland pointer motion; IPC cursor warping alone was not equivalent.
- With user approval, persisted `focus_follows_mouse no` in `/home/shu/work/gral/arch/sway/config`
  and applied immediately. Desktop-wide click focus; no plugin focus stealing or fake green indication.

## Automated acceptance

- Python: 118 passed; CTest: 4/4 passed.
- Keyboard: 199 basic checks, 1012 ordered pair/release sequences, plus all seven held degrees with G/G/V/V, repeat suppression and final release.
- Generic ModifierTap: 2040 overlap sequences. Ctrl remains a generic test input, not a registered product action.
- Real CLAP: all seven held degrees move up twice/down twice, checked for lowest-note direction, note count, exact return and complete Note Off.
- Legacy state, 19 parameters, GUI creation/resize/recreation, 12 sample-rate/block combinations, mixed MIDI during theme changes and independent-instance restoration passed.

Local evidence: `target/chordlab-gv-focus/`. Previous binary/project copies are rollback backups, not a parallel product.
This does not recertify all 98 sounds, all physical keyboards or other operating systems.

## Local Bitwig validation

Backed up and saved Library, closed editors before clean Bitwig exit, installed 0.1.8 and reopened the same project.
Holding C and tapping G changed Cmaj7/C4 to Cmaj7/E4, with sfizz and track output meters responding.
V returned the voicing; releasing the chord cleared held highlights. Shift down stayed red,
standalone release turned Sustain green, another tap turned it off, and C+Shift did not toggle it.
Esc/Ctrl taps no longer moved voicing. Native pointer motion over sfizz kept Keyboard green;
clicking sfizz turned it red and clicking back restored green.
Restored sfizz Controls, Sustain Off and Keyboard On, and saved Library.

Installed `~/.clap/Chord Lab.clap`, SHA256:
`7f3cc182b906794f994a315168e4d8d42d6e78dd6332fa2d89e2ba66c38e8cfe`.
REAPER synth.rpp and Guitar Frontend binary hashes remain unchanged.
