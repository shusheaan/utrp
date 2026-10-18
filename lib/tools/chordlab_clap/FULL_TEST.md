# CLAP 0.1.3 full regression: 2026-10-17

[中文](FULL_TEST.cn.md)

## Scope and result

Linux x86_64, REAPER 7.78, Sway/X11. Tested the installed `Chord Lab.clap`,
SHA-256 `a17a614adaebb33fb31b346d51afca49610e75203a23d27151be448acec41c44`.
Covered regressions pass; this is not universal host, platform, or physical-device certification.
Native JSFX remains a historical isolated-test reference, not a second maintained product.

| Check | Result |
|---|---|
| Python / C++ | 113 / 2 tests passed |
| Library lifecycle/startup | 36 lifecycle assertions; default piano, idempotency and timeout checks passed |
| MIDI A/B | 2,379/2,379; ordered MIDI bytes and block-relative sample offsets match |
| Save/reload / host parameters | 7/7, 22/22 |
| Mixed Track FX / Input FX | 42/42 each, checked against independent expected events |
| Actual Input FX recording | Six notes per lane; exact pitch/channel/velocity, positive lengths |
| Production library | 95/95 patches generate chord and ordinary MIDI audio; one online instrument, solo, armed input and instrument editor |
| ABI/lifecycle | 18 parameters, MIDI ports, GUI create/resize/recreate, independent instances, state, 12 sample-rate/block-size combinations |
| GUI | No long-hold retrigger, inversions, semicolon reset, Tab, Enter/mouse Sustain, Keyboard toggle, focus release/recovery, Space does not start transport |
| Real REAPER restart | Default Acoustic Piano, one shared CLAP Input FX, no legacy VKB, computer-keyboard audio |

The restarted session identifies `Keystation 61 MK3` with input armed and monitoring enabled.
Measured computer-keyboard piano peak: `0.42076608538628`.
Preserved 102 track identities/order, 93 Surge engines/wavetables, two sfizz states,
the basic-keys folder effect, all track/master gains, and the exact pre-test CLAP state.
Temporary test input removed, isolated instances stopped, production `synth.rpp` saved and open.

## Harness issues and reruns

- The initial library audit assumed a zero Master meter proved mute. Meter taps can be
  pre-fader. It now sets/checks both `D_VOL=0` and `B_MUTE=1`, restores both, and passed
  the full library rerun.
- An overlapping isolated GUI stole focus and interfered with the first state test.
  Reloading the saved baseline and running state/parameter tests serially passed.
  The initial failure remains in the evidence and is not counted as a pass.
- An early production GUI test hit the temporary Input FX count guard; it was rerun
  after cleanup. Keyboard was disabled during diagnostics and correctly produced no
  notes; enabling it passed GUI and post-restart audio checks.
- `mixed_record.lua` now permits versioned `*-input` scratch directories while still
  rejecting production projects.

This test round changed harnesses and records, not the musical core or deployed binary.

## Not certified

Physical finger/pedal performance and USB reconnect; pixel-level gray-note display with
mixed physical input; Bitwig; macOS/Windows; prolonged stress; multiple displays/forced
tiling; subjective sound quality. Spark GO is disconnected: actual output is
`eq_woo_in → WooAudio`, not a passed Spark routing test.
The REAPER-owned `No preset / Param / MIDI / UI` row is unchanged.

## Evidence and reproduction

Machine record: `target/chordlab-full-0.1.3/acceptance.json`. TSV, results, scripts and
state evidence are under its `evidence/`; unit and ABI logs are at the directory root.

Create isolated profiles with `stage_port.py`; run `ab_test.lua`, `state_ab.lua`, then
`parameter_ab.lua`. Run `mixed_ab.lua` / `mixed_record.lua` in separate scratch profiles.
Do not overlap GUI injection with tests that open windows.
See [migration notes](../library/CLAP_MIGRATION.md) for the library audit; do not play,
switch projects or save while it runs.
