# Bitwig trial acceptance: core workflows over 30 days

[中文](TRIAL_ACCEPTANCE.cn.md) · [Environment and file map](WRAPUP.md) · [Grid example](GRID_LAB.md)

## Goal and decision

Confirmed on 2026-10-18: evaluate recording, repeated takes, sound design, high-level control panels,
Grid concepts, and repeatable AI / scripting / custom-plugin assistance rather than cataloging features.
Thirty days is a planning window; the account and application determine the actual trial expiration.

Choose Bitwig as the main DAW if core manual workflows feel good, save/restore is reliable, important
automation is repeatable, and the user approves hands-on. Not everything must be scriptable.
CLAP or Controller API availability does not imply access to every host operation. Preserve REAPER projects.

`- [ ]` means not accepted; `- [x]` means accepted. Separate software tests from user performance tests.
Existing WRAPUP / GRID_LAB evidence does not automatically pass the scenarios below.

## P0: recording and retakes

- [ ] Record physical-keyboard and Chord Lab MIDI; replay matches performance without stuck notes.
- [ ] Record real guitar dry while monitoring effects; check input, latency, monitoring, and feedback risk.
- [ ] Set a start / range, return to it, use count-in, record selected bars, stop, and immediately retry.
- [ ] Record at least 3 passes; verify retention for the chosen mode, boundaries, notes, and tails.
- [ ] Verify take selection / editing separately for audio and MIDI; do not assume identical comping features.
- [ ] Retake and undo without destroying the only previous recording; recover from mistakes.
- [ ] Save, close, and reopen with media, takes, edits, plugin states, and routing intact.
- [ ] User completes prepare → record → retake → choose → save; record friction and actual steps.

Real guitar tests require Spark GO and user performance. Synthetic unattended tests do not replace them.

## P1: sound design and a unified control panel

- [ ] Map useful parameters of one Surge sound to a Remote Controls page with English labels.
- [ ] Consider Brightness, Motion, Space, Attack, Release, Width, Drive, Output; keep only useful controls.
  Record each macro's targets, limits, and direction rather than forcing eight controls.
- [ ] Test multi-target macro limits, level changes, automation writing, and playback.
- [ ] Save project state, reusable preset, and mappings; reopen and load in a new project to check persistence.
- [ ] Save A / B sounds and renders of identical MIDI; record loudness differences during comparison.
- [ ] User can make a meaningful variation from the panel without hunting through the plugin UI.

## P2: Grid concepts

- [ ] Explain source, timing, pitch, dynamics, space, and output using Warm Fractal Veil.
- [ ] Build a small understandable generative variation with constrained pitch, sparse triggers, slow modulation;
  explain why each additional module is needed.
- [ ] Compare fixed loops, probability, and timbral modulation; distinguish audio motion from MIDI generation.
- [ ] Expose a few high-level macros; check safe ranges, stop/restart behavior, CPU, and persistence.
- [ ] Save a playable project / preset, short render, and structure notes; user edits one part and hears its effect.

The existing Grid example passed scoped save/reopen and output checks, not subjective or teaching acceptance.

## Cross-cutting: AI, scripts, and custom plugins

- [ ] Classify each critical action: native UI, Controller API, GUI automation, custom CLAP, unsupported / unverified.
- [ ] Check interfaces and limits separately for selection, macros, transport, recording, and saving.
  Do not describe mouse automation as a stable API.
- [ ] Make automation logged and recoverable, with safety boundaries for level changes and recording files.
- [ ] Run each chosen automated workflow 3 times; log success rate, focus/dialog dependencies, and recovery.
- [ ] Regress Chord Lab / Guitar Frontend state, reopen, mixed input, and focused shortcuts in target scenarios.
- [ ] Add custom plugins only for identified gaps, documenting the problem before implementation.

## Sequence and preservation

Suggested sequence, not a scheduled background job:

1. P0 recording, retakes, persistence.
2. P1 sound panels, automation, preset reuse.
3. P2 Grid and generative structures.
4. A short integrated piece, weak-point retests, and a main-DAW decision.

Each session retains **project snapshots, procedure notes, audible results, conclusions / next steps**.

- Proposed large-file location: `~/storage/daw/Bitwig Trial/<scenario>/`, outside Git; not created by this checklist.
- Use English project / track / clip / macro / preset names. Do not destructively test in production Library.
- Keep docs, scripts, configuration, and test source in UTRP; transient evidence in `target/`, important conclusions in docs.
- Example snapshots: `Recording-01-Baseline`, `Recording-02-ThreeTakes`, `Sound-01-A`.
- Check external audio, samples, plugin versions, and controller dependencies, not just .bwproject.
  Autosaves are not a complete backup.

Record date, version, device / buffer, steps, expected / actual outcome, evidence paths, manual / automated
execution, user-tested status, and remaining issues. Failed items remain unchecked with a reason.

## Current record

- 2026-10-18: checklist established; no new recording, take, or automation acceptance this turn.
- Existing scoped Grid results are in GRID_LAB; Library / CLAP results are in WRAPUP.
- Next: a separate Recording Lab for the record / retake / save loop, before expanding sounds or complex Grid work.
