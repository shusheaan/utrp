# 0.1.6: single CLAP product and revalidation

[中文](RETIREMENT.cn.md) · [Usage](README.md)

## Product boundary

Maintain only `Chord Lab.clap`, stable ID `org.utrp.chordlab`. Retired JSFX installers,
Lua/VKB entry points, the old VKB map and obsolete binaries are removed. The production
Open Chord Lab action only opens the existing shared CLAP; it cannot install legacy JSFX.

**The embedded EEL/JSFX engine is current source, not an obsolete product.** The six
engine files, notation image and license in `../chordlab/` remain build inputs. All eight
assets match the embedded archive byte for byte. Native JSFX used by regression tests
is a reference fixture, not a second maintained/deployed product. User project backups
and historical evidence remain; old projects are not implicitly converted.

## Root cause and fix

System auto-repeat begins at 200 ms. The old physical-state release snapshot could
clear a held key before a queued repeat arrived, treating that repeat as a fresh press.
Tab/Esc could therefore act more than once. Skipping some JUCE key-down queries alone
did not resolve the race.

0.1.6 uses one ordered X11 key/focus event stream with `XkbSetDetectableAutoRepeat`.
Only real KeyRelease ends a held key; physical snapshots initialize/resynchronize
inactive capture. Mapped keys and left Ctrl/Shift share the stream. Focus loss releases
computer notes and cancels pending modifier taps; refocus does not trigger pre-held
keys. Keys released outside the editor clear the focus-loss block so the first fresh
press after returning is accepted. Brief native focus out/in also releases notes without relying on a 20 ms timer
catching the intermediate state. JUCE callbacks drain events immediately; the timer
is a fallback. Unsupported X11 capture shows an explicit error.

A separate focus boundary left the JUCE component cache focused while the host owned
native focus; requests with an older user timestamp could be ignored by X11. Content
clicks now explicitly focus the viewable peer with `CurrentTime` on mouseDown/mouseUp;
indication uses actual native focus. The timer never steals focus from another window.

Harmony algorithms, 18 parameters, state format, hardware MIDI velocity and plugin ID
are unchanged.

## Evidence and scope

Final binary SHA-256 and result index: [`retirement_acceptance.json`](retirement_acceptance.json).
Raw local evidence: `target/chordlab-retirement-0.1.6/`. Failed attempts and preliminary
results are retained separately rather than attributed to the final binary.

- 96 Python tests scoped to current CLAP/engine/Library; 3 CTest suites: 188 keyboard checks, 924 ordered mapped-key/release
  pair sequences, 2040 Ctrl/Shift combination sequences and 11 control queue checks.
- Isolated REAPER: 2379 MIDI A/B cases comparing bytes, order and block offsets;
  7 state checks, 22 parameter checks, 42 mixed-input checks each in Input FX and Track FX.
- Independent CLAP host: lifecycle, ports, 18 parameters, 8 pending parameter writes,
  GUI, cross-instance state, 44.1/48/96 kHz × 32/64/256/1024 frames;
  Library lifecycle and startup-wait tests.
- Real desktop: 83 XTest checks including seven degrees, twelve tonics, retired keys,
  left-hand controls, modifier cancellation, held-note focus loss/refocus, rapid native
  focus transitions, and Tab holds from 190 ms to 1.2 s. Another 28 outside-release/refocus
  repetitions passed 56 assertions. The final focus-loss target is an inert X11 window: earlier tests focused the DAW, allowing OS repeat to invoke host actions and open competing windows. The full original project baseline was restored before retesting.
- Production library: all 95 patches checked for chord-control and ordinary MIDI audio,
  exclusive online/solo/armed/window routing and disabled old VKB. Master is muted during
  testing; cleanup restores user settings.
- Baseline comparison: 102 track identities, 93 Surge engines/wavetables, 2 sfizz states,
  folder effects and all track/master gains preserved; save/restart and playable-state check.

This is bounded regression evidence, not a mathematical guarantee for every host,
hardware device or timing. Physical hand-played MIDI, Bitwig, macOS/Windows, native
Wayland and every host global-shortcut configuration are not certified. Device enumeration,
routing and injected MIDI audio tests do not substitute for a human playing the device.

One nonstandard host launch left stopped CLAP processing inactive; starting transport
once activated it. Normal-launcher cold starts passed without transport. The deeper host
cause is not established and is not attributed to instrument patches or plugin DSP.

## Daily use

Open `synth.rpp` and select a patch: `hardware MIDI / computer keys → shared Chord Lab
Input FX → selected instrument → FX`. Only the shared input track is armed; do not add
another Chord Lab to every instrument. Computer keys require a focused green Keyboard
button; hardware MIDI does not require editor focus. Z/X=6/7, C=1, A/S=2/3, D/F=4/5;
Esc moves left, standalone left Ctrl release moves right, Space restores position,
standalone left Shift release toggles Sustain, Tab cycles triad/seventh/ninth. Overlap
with another key or focus loss cancels pending modifier-tap commands.

## Additional repository checks

`cargo test --offline` and `cargo clippy --offline --all-targets -- -D warnings` passed.
An unscoped root `pytest` attempt had 12 collection errors: archived `target/` tests
were recollected or needed a GUI, `soundfile` was unavailable, and old tests imported
a missing `scripts` package. We do not claim all repository Python tests passed; the
96 current plugin/engine/Library tests passed independently.
