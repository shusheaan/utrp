# Mono-only wrap-up — 2026-10-18

[中文](MONO_ONLY.cn.md)

## Decision and implementation

Real playing rejected the dyad experiment. Guitar Frontend 0.2.1 removes Mode, the second-note meter and dyad runtime/build dependencies. Retired runtime sources and deployment backups are archived under `target/mono-pill-wrapup/retired-dyad-runtime/`; offline experiments remain historical research, not product features.

Detect, stable CLAP ID, MIDI channel 2 and bit-exact dry audio pass-through remain. Import both v1 and experimental v2 states, validating all fields transactionally. Either retired Mode value restores mono; other settings survive. Save v1 states for compatibility with older mono builds.

Accuracy first: `engine.cpp`, `engine.h`, `defaults.toml` are unchanged (64/8/24 ms frame/hop/stability). Earlier short-window experiments produced octave errors; conservative alternatives offered insufficient demonstrated benefit. No faster settings deployed, no guarantee of perfect recognition or hardware end-to-end latency.

## Verification

- Release and UBSan: two CTests each passed, including 510 pitch/waveform/rate cases, 45 false-low-note regressions, noise, onset/release, melodies, 40 CLAP rate/block/precision cases, event backpressure and state compatibility.
- 631 Python tests across mono research, Chord Lab and wrapper passed; six Chord Lab CTests and installed-binary GUI CLAP probe passed.
- Three historical recordings, 20,604 output frames, byte-identical to the stable mono replay. This establishes non-regression, not ground-truth correctness for every frame.
- Bitwig 6.1.4 Library saved, restarted and loaded new plugins. Mode absent, Detect On preserved. Synthetic E4 reaches shared Chord Lab and releases; computer keyboard still plays/releases.
- Initial output capture included decaying reverb from the preceding chord-button test. Evidence retained and test repeated after decay: six seconds of stereo output had a peak of zero. No new real-guitar accuracy trial claimed.

## Locations

- Project: `~/storage/daw/Library/Library.bwproject` (outside Git).
- Shared installed binaries: `~/.clap/Guitar Frontend.clap`, `~/.clap/Chord Lab.clap`; running hosts must reload.
- Mono sources: `lib/tools/guitar_frontend/`. Pill UI: `lib/tools/chordlab/{ui.jsfx-inc,theme.toml,generate_theme.py,chordlab.jsfx}` and `lib/tools/chordlab_clap/state_button.h`.
- Backups, hashes, builds, replay evidence and screenshots: `target/mono-pill-wrapup/`.
- Spark GO capture_MONO restored to Bitwig in1. Analysis precedes DAW effects; existing 2→15 mapping remains display-only. Hardware Spark effects cannot be undone by the detector.
