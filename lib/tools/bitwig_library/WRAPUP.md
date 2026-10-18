# Bitwig / UTRP wrap-up and storage map — 2026-10-18

## Authoritative current state — final wrap-up 2026-10-18

Earlier sections below are historical milestones. Current versions: Chord Lab **0.2.12**,
Guitar Frontend **0.2.1 mono**, Library controller **0.7**, center-first floating layout.
Preferences now physically reside on Storage, not merely in periodic snapshots. See
[live storage/recovery](../daw_backup/README.md) and
[final validation and limits](../../../review/2026-10-18/project-health.en.md).

## Historical milestones below

## Floating plugin layout — 2026-10-18

Enabled a Sway policy for external Bitwig plugin editors: Chord Lab anchors the right edge, other editors pack right-to-left and wrap below, preserving the track area. No sound, internal zoom or audio routing changes. Live checks covered Surge XT Effects, Dragonfly Hall, Surge XT and sfizz, including four simultaneous editors, close/reopen, manual dragging and focus preservation. All 27 layout/Library tests and strict mypy passed. See [`plugin_windows/README.md`](../plugin_windows/README.md). Library saved with the Soft Prism three-editor layout; this was not a Spark GO live-audio acceptance test.

## Latest: Ambient Guitar / controller 0.6

Four live guitar FX tracks were added under **Ambient Guitar**. Audio effects are independent of the shared, display-only guitar detection path. See [routing, controls, files, and validation](AMBIENT_GUITAR.md). This supersedes historical track counts below: the Library now has 113 tracks including groups and Master.

## Latest wrap-up: Chord Lab 0.2.10 and shared routing

This section supersedes historical version/device status below. The user accepted the UI and saved the project; wrap-up makes no further host or project edits.

- **Outer whitespace:** window grows from 884×683 to 920×703 while the canvas stays 884×683. Side margins grow from 18 to 36 px, top from 10 to 20 px, bottom gains 10 px. Fonts, capsules, S/A circles and diagrams are not scaled.
- **Implementation:** `[editor]` in `lib/tools/chordlab/theme.toml`, `generate_theme.py`, and canvas/control/error-label offsets and resize limits in `lib/tools/chordlab_clap/editor.cpp`. Configuration validation and dimension regressions added; release 0.2.10.
- **Shared routing:** the top `CHORD LAB - shared MIDI input` track contains `Note Receiver → Chord Lab`. The receiver taps Guitar Frontend on the guitar track; its Source FX maps channel 2 to display-only channel 15. Hardware MIDI and computer chords use that same shared Chord Lab to feed the selected audition sound. There is not a detector/Chord Lab pair on every sound track; independent instances do not automatically share inputs.
- **Guitar:** detected notes highlight Chord Lab without triggering the downstream piano/synth. Guitar audio remains independent. No detection algorithm or routing changes in this release.
- **Validation:** 556 Python tests, eight CTests, build and installed CLAP probes passed. Actual Bitwig window is 920×703; aligned top diagrams and key rail (excluding Active state) are pixel-identical to the previous canvas. Added margins are solid `#585858`. Live Sustain clicks passed, ending S Off / A On; Spark GO output and capture→Bitwig in1 connections remained intact.
- **Locations:** project `/home/shu/storage/daw/Library/Library.bwproject`; shared binary `/home/shu/.clap/Chord Lab.clap`. REAPER also uses the updated appearance when reloading that binary, but projects and instance routing remain host-local.
- **Evidence:** `target/editor-padding/` contains logs, screenshots, pre-update backups and the user-saved `Library-user-saved-wrapup.bwproject` snapshot with `wrapup.json`.
- **Limits:** no fresh full-library audition, physical MIDI performance or real-guitar accuracy validation in this layout release. No Git commit/push or REAPER project deletion.

## Current update: display-only guitar input (0.2.5)

- MIDI channel 15 is reserved for display-only analysis: Note On/Off update piano, fretboard and staff highlights without forwarding notes. Controllers, sustain and pitch bend on this channel are also swallowed.
- Physical keyboards use channels 1–14; computer commands retain channel 16. Guitar and keyboard ownership remain independent even at the same pitch: guitar cannot sustain or suppress an instrument note.
- No new switch or parameter. The 21 parameters, stable CLAP ID and v3 state format remain unchanged; existing states load directly.
- Guitar Frontend still emits channel 2. Library's Note Receiver Source FX maps 2→15 before the shared Chord Lab, with Mutes Input OFF.
  Only the received guitar branch is mapped; physical keyboard channel and velocity remain unchanged. Updating the shared binary does not rewrite old REAPER routing: other hosts need the same analysis-branch mapping to channel 15.
- Spark GO USB input is connected, with guitar Monitor ON and Detect ON. Its audio fader remains at −∞ to avoid duplicating Spark GO direct monitoring. Future DAW effects must remain after the detector.

Validation: 562 pytest cases, six CTest suites and the real CLAP probe pass, covering all 128 display pitches, controller isolation, same-note mixed input, computer release in both modes, focus loss and repeated Note On.
Evidence and pre-deployment backups: `target/chordlab-guitar-display/`. This is not a real-guitar accuracy or latency acceptance test, and does not claim 100% pitch recognition.

Post-deployment Bitwig check: Library was saved, closed and reopened; the Source FX 2→15 mapping persisted, with Acoustic Piano selected.
A 220 Hz synthetic signal injected into the guitar input highlighted A3 in shared Chord Lab with no piano/master meter activity. The computer C chord key subsequently produced instrument meter activity, then released its highlights and audio.
The temporary PipeWire test source exited; Spark GO capture→Bitwig in1 and Bitwig out1/out2→Spark GO output remain connected.
Library was saved again and focus restored to Chord Lab. Synthetic checks do not replace real-guitar or physical MIDI keyboard acceptance; user listening confirmation remains pending.

This section supersedes the historical guitar 2→1 instrument routing and disconnected-hardware status below.

## 2026-10-18 follow-up: Chord Lab 0.2.0 dual voicing

Current controls are **H/L navigation, J Piano, K Guitar**, replacing G/V.
Adds guitar-shape lookup, independent position memories, mode dots and fingering outlines; palette unchanged.
[Features, limits and verification](../chordlab_clap/GUITAR_VOICING.md).
Library routing, instrument presets and Guitar Frontend were not modified this round.


[中文](WRAPUP.cn.md)

## Follow-up wrap-up: Grid example, trial priorities, final palette

This is a later 2026-10-18 update. Earlier migration and acceptance records below remain historical,
not a claim that all tests were rerun during this follow-up.

- **Final Dark palette:** white keys match the background at `#323232`; both black-key fills are
  `#000000`. This supersedes the intermediate black-white-key / gray-black-key scheme.
  Dividers, frame, highlights, Bright mode, staff, fretboard, keys, and MIDI behavior remain unchanged.
- **Implementation/deployment:** `lib/tools/chordlab/theme.toml`, `generate_theme.py`, generated
  `theme.jsfx-inc`, keyboard rendering in `ui.jsfx-inc`, and `tests/test_theme.py`.
  Rebuilt/deployed `~/.clap/Chord Lab.clap` as a 0.1.10 asset revision and restarted Bitwig.
  REAPER uses the same new binary on reload; Dark/Bright remains per-instance state.
- **Scoped checks:** 118 pytest cases, 4 CTest groups, and the real CLAP probe passed.
  Both keyboard regions were visually and pixel-checked in Bitwig.
  Evidence and previous plugin/project backups: `target/chordlab-gray-white-black-keys/`.
  Installed SHA-256: `ef47c789ad7bba9945d758ae810fcc07b3480114c82b8f9f4ee71ecc98ef210e`.
- **Grid Lab:** `~/storage/daw/Grid Lab/Grid Lab/Grid Lab.bwproject`, adapted from Essentials'
  Fractal Machine - Divine Radiance; 72 BPM, 16-bar C#m7. `Preview.wav` is beside the project.
  Not a from-scratch network, exact Endless recreation, or full random arranger.
  Save/reopen and audio output were checked; see [Grid Lab](GRID_LAB.md).
- **Trial priorities:** recording, repeated takes, retakes and persistence first; then Remote Controls,
  automation, Grid concepts, AI / scripting / custom-plugin boundaries.
  The saved [trial checklist](TRIAL_ACCEPTANCE.md) describes pending acceptance, not completed tests.
- **Delivery:** Library and Grid Lab saved, both tabs retained, returned to Library / Chord Lab.
  REAPER projects retained; no Git commit or push. No new full 98-sound, physical MIDI, or real Spark GO acceptance.

## Current state

The saved main project is `/home/shu/storage/daw/Library/Library.bwproject`, with C# Minor /
Chord Lab C#m/E, Acoustic Piano, Sustain OFF, transport stopped. Versions: Chord Lab CLAP
0.1.10, Guitar Frontend CLAP 0.1.2, Library controller 0.5. Both DAWs share the installed
custom CLAPs, not their project state or host scripts. Hardware acceptance remains incomplete:
Spark GO is absent, and real guitar/physical MIDI mixed performance still needs the user.
Original REAPER projects are retained.

## Cumulative changes

- Migrated all 95 original sounds and retained three ambient pads: 98 sounds, 108 tracks
  including groups, shared input, guitar and Master. Bitwig names are English.
- Compared 95 original instrument states. Surge parameters, wavetables and tuning were
  retained. sfizz may add default CC64=0 when resaved; this explicit exception is documented.
- Replaced Basic Keys ReaVerbate with approved Bitwig Reverb, not an identical algorithm.
  Added downstream Tool gain to preserve C2-distant's out-of-range original fader gain.
- Library controller provides exclusive sound audition and opens instrument/shared Chord
  editors. Disable `Exclusive audition + editors` before ordinary multitrack composition.
- Verified Poly Grid loading, editor and audio; temporary test track and notes were removed.
- Chord Lab gained Dark/Bright appearance, thicker separators and brighter note markers.
  Unsuccessful transparent outer corners were removed in favor of clean rectangular edges.
  Sustain/Keyboard are red/green dots; Panic and the top shortcut banner are gone.
- Current keys: ZX=6/7, AS=2/3, C=1, DF=4/5; V/G navigate voicings while holding chords;
  Space toggles Sustain; Tab cycles triads/sevenths/ninths with per-degree memory.
- Focus/release safeguards remain. Sway uses click-to-focus (`focus_follows_mouse no`).
  Relative minor/major labels such as Am/C retain the original embedded harmony engine.
- Controller 0.5 synchronizes all seven diatonic modes in both directions. Plugin changes
  retain the host mode; host changes map its parent-major pitch set. This is not a modal
  tonic/degree engine. Unsupported scales pause sync; host wins initialization/resumption
  and simultaneous conflicts. Playback/held-note deferral remains.
- Shared input uses Note Receiver → Chord Lab, receiving Guitar Frontend with Source FX
  Channel Map ch 2→1 and Mutes Input disabled. Shared note ownership prevents releasing
  one input from cutting off the same pitch still held by another.
- Guitar analysis precedes DAW effects; hardware effects already in USB audio cannot be
  undone. The shipped detector is a monophonic experiment, not reliable polyphonic tracking.

## Storage map

Here `~` means `/home/shu`; source paths below are relative to `~/work/utrp/`.

| Category | Location / purpose |
| --- | --- |
| Repository | `~/work/utrp/`: source, configuration, tests, documentation, original FXP |
| Chord engine | `lib/tools/chordlab/`: EEL/JSFX harmony, MIDI, notation and theme sources embedded in CLAP |
| Chord CLAP | `lib/tools/chordlab_clap/`: C++ wrapper, GUI, focus/keys, state, build and tests |
| Guitar CLAP | `lib/tools/guitar_frontend/`: monophonic DSP, CLAP audio/MIDI/params/state and tests |
| Polyphonic research | `lib/tools/guitar_poly/`: experiments, not a shipped polyphonic detector |
| Bitwig integration | `lib/tools/bitwig_library/`: migration, state checks, controller/key sync and tests |
| REAPER integration | `lib/tools/library/`: retained original library/startup/migration tools |
| Original presets | `lib/surge/`: 88 Git-tracked FXPs; project edits do not rewrite them |
| Installed custom plugins | `~/.clap/Chord Lab.clap`, `~/.clap/Guitar Frontend.clap`: shared by both DAWs |
| Installed controller | `~/Bitwig Studio/Controller Scripts/UTRP/`: control, key-sync and config JS files |
| Bitwig executable | `~/opt/bitwig-studio-6.1.4/opt/bitwig-studio/bitwig-studio`: native 6.1.4 Trial, ~651 MiB installation |
| Bitwig configuration/content | `~/.BitwigStudio/`: preferences/cache/logs; installed-packages is ~7.5 GiB, including Essentials |
| Bitwig user library | `~/Bitwig Studio/Library/`: user presets/templates, not our main Library project |
| Main project directory | `~/storage/daw/Library/`: ~37 MiB including presets, migration snapshot and automatic backups |
| Main project file | `~/storage/daw/Library/Library.bwproject`: ~2.3 MiB; use this, not Library-migration.bwproject |
| Added pad presets | `~/storage/daw/Library/Presets/`: Warm Veil, Dark Choir, Silver Haze |
| Piano sample library | `~/storage/daw/samples/SalamanderGrandPianoV3_44.1khz16bit/`: ~1.2 GiB, SFZ/Soft/Retuned mappings and WAV |
| Original REAPER projects | `~/storage/daw/synth.rpp`, `~/storage/daw/Guitar Lab.rpp`: retained, not auto-updated by Bitwig |
| Backups | `~/storage/daw/Backups/`, `~/storage/daw/Library/auto-backups/` |
| Build/evidence | `~/work/utrp/target/`: ~3.5 GiB, ignored by Git; dependencies, binaries, captures and logs |

System instruments: `/usr/lib/clap/Surge XT.clap` (also Effects and VST3),
`/usr/lib/vst3/sfizz.vst3`, `/usr/lib/lv2/sfizz.lv2`. Bitwig uses sfizz VST3 while the old
REAPER project uses LV2: different plugin formats sharing samples. The current Scala path
still points to `/usr/lib/lv2/sfizz.lv2/Contents/Resources/DefaultScale.scl`; preserve that
dependency when moving the setup or removing LV2.

Surge skins live in `~/.Surge XT/Skins/`; default Modern Dark Blue / 125%, with Royal and
nine Andromeda variants also installed. sfizz Dark preference is in
`~/.config/SFZTools/sfizz/settings.xml`; Sway focus configuration is `~/.config/sway/config`.
Application launchers live in `~/.local/share/applications/`; `utrp-bitwig-library.desktop`
opens the main Storage project. Residual Flatpak data is not the active installation and
was not deleted during this wrap-up.

## What a project saves

A `.bwproject` stores tracks/groups, routing, MIDI/clips, automation, device chains and
plugin-provided state. It does not include Bitwig or plugin binaries, nor necessarily every
sample referenced internally by a third-party plugin.

- Surge's current state is saved with the project; reusable FXPs remain separate snapshots.
- sfizz stores settings/paths in state; the piano WAV library remains external in Storage.
- Controllers, skins and system device routing remain external dependencies.
- This resembles REAPER's project-plus-external-media arrangement, but the formats are not
  interchangeable. Copying only the project file does not transfer the full environment.
- `File → Collect and Save` collects media known to Bitwig; do not assume it packages
  third-party sampler internals or plugin executables.

Reference: [Bitwig Project Panel](https://www.bitwig.com/userguide/latest/the_project_panel/).

## REAPER sharing

The existing synth.rpp Chord state was extracted read-only and loaded into the installed
CLAP: state compatibility and default Dark passed. REAPER itself was not launched and its
project was not changed. Reloading uses the current plugin; an instance explicitly saved
as Bright in the future retains its own setting. Shared code does not synchronize keys,
chord memory, tracks or preset edits between separate projects. Bitwig global-key sync is
a host-specific controller feature, not automatic REAPER integration.

## Acceptance and limits

Wrap-up reran 198 Python tests, four Chord CTests and two Guitar CTests, all passing.
Installed Chord X11/CLAP probe, installed Guitar host probe and original RPP-state
compatibility probe passed. `xvfb-run` was unavailable on the first attempt; no software was
installed, and validation succeeded using existing XWayland instead.
Installed CLAPs match their build artifacts byte-for-byte; all three controller files match
source; the original RPP hash is unchanged. Each main SFZ has 641 existing sample references;
the SoftPiano include also exists, with no missing references.

Earlier session evidence covers 98/98 sound checks and 98/98 after reopening, eight synthetic
guitar pitches, mixed note release, keyboard/focus, Grid and bidirectional keys. The entire
98-sound matrix was not repeated during wrap-up. Keystation is visible to the system; Spark
GO is absent. Guitar remains No input / Monitor OFF. HDMI output is not Spark monitoring
acceptance. Real guitar accuracy/latency/noise and physical mixed performance remain pending.
Earlier Surge bus-activation messages and sfizz/X11 shutdown issues are not proven resolved
merely by successful audio checks. Temporary probe TCP port 19671 is closed.

Evidence: `target/session-wrapup/`, `target/bitwig-diatonic-sync/`,
`target/bitwig-guitar-grid/`, `target/bitwig-migration/`.

## Git and backups

Storage is outside this repository, so projects/WAV/backups are not committed here;
`target/` is ignored. Custom source is in UTRP, but many changes remain modified/untracked:
being in the directory is not equivalent to a Git commit or remote backup. Nothing was
committed or pushed. Installed copies are runtime artifacts: edit source, test/build,
deploy, then reload the DAW. Back up source, Storage and installation/configuration records
separately, not only `.bwproject`.

### Cross-instrument window recheck

Verified 13 live layouts: six Basic Keys, three Pads and four Ambient Guitar chains. Checked floating, bounds, pairwise spacing and main-window geometry. Fixed false overflow caused by small FX fragmenting space before a large instrument opened. Added 340 opening-order regressions (20 failures before, none after); total 368 tests and strict mypy pass. Cross-track five-editor mixtures used measured-dimension computation, not live simultaneous editors under exclusive audition. Evidence: `target/plugin-window-combinations/`.

Also fixed occasionally remembered oversized Surge XT Effects editors on cross-track reopen: reset only FX to 600×490 on opening/overflow, never the Surge XT instrument.


## 2026-10-18: centered editors and pedal baseline (0.2.11)

This supersedes earlier live-state notes: Library was backed up, saved and reopened with Chord Lab 0.2.11. Acoustic Piano is restored and both Bitwig outputs connect to Spark GO. Recording Bitwig alone while playing the computer C chord measured peak 0.3421 and RMS 0.02354. The complete sound library was not retested; synthetic MIDI is not physical-pedal acceptance.

- S indicates the pedal-up sustain baseline: red means press for sustain; green means press to temporarily cancel sustain; release restores the baseline. Space/click changes the baseline, not pedal input. Held keys are not muted. Existing focus-loss baseline cleanup remains. CC64 uses threshold 64; hardware polarity must be correct. Release and press again after reload.
- Per-channel pedal state is implemented in `chordlab/midi.jsfx-inc` and engine memory; CLAP tooltip, binary probe, `sustain_tests.cpp` and bilingual mixed-input instructions are updated. Installed binary: `~/.clap/Chord Lab.clap`.
- Library controller 0.7 opens shared Chord plus the instrument/first guitar FX for sound tracks, or local Chord for auxiliary tracks. Previous known editors close without changing auxiliary audio routing. Scope is the first four top-level devices, not arbitrary nesting. After closing all editors on the current track, select another track and return to reopen them.
- Floating editors now prioritize the center: Chord alone centers; Chord and primary plugin center as a group; extra FX use right-side and surrounding free space. Service and controller are deployed. Live piano, Surge, raw-guitar single editor, Soft Prism triple editors and Cloud Halo four editors passed floating/bounds/non-overlap checks.
- Validation: 926 pytest cases, nine CTests and installed CLAP probe pass; layout strict mypy passes. Evidence: `target/pedal-baseline/` and `target/plugin-windows-center/`. Project remains `/home/shu/storage/daw/Library/Library.bwproject`; runtime project and local backups are outside Git. No commit or push.
- Pending: user verification of physical pedal press/release for both baselines. Guitar input still showed missing in this session; working Spark GO output does not prove guitar input mapping works.

### Keystation Transport follow-up

Captured all eight physical buttons, confirming Mackie/channel 1. Added and installed `Keystation.control.js` plus `.config.js`; Bitwig reports ready. Existing Generic musical input is retained, Volume CC set to 7 with Catch takeover. New controller uses Transport only and creates no Note Input. Maps transport, track navigation, one-bar movement and home, with navigation blocked during recording. Removed the unrelated automatically discovered Spark GO Generic MIDI controller without changing audio output. 927 pytest cases, nine CTests and the extended installed CLAP CC1/7/11/bend probe pass. Awaiting user host-operation feedback; no recording test take was created in production Library. See [KEYSTATION.md](KEYSTATION.md) and `target/keystation-controls/`.


### Spark GO guitar input restored

Bitwig had selected GB203 HDMI without capture. Switched to Spark GO USB, restored mono capture and stereo playback, inspected the raw detector and shared Note Receiver, saved Library and returned to Glass Air. Shared display routing and four FX recipes are unchanged. Live user confirmation with direct monitoring off remains pending. See the final section of [AMBIENT_GUITAR.md](AMBIENT_GUITAR.md); evidence: `target/guitar-routing-restore/`.


### Momentary pedal investigation (2026-10-18, new binary reload pending)

Physical CC64 showed reversed polarity: down 0/up 127. After the user restarted Keystation with the pedal released, capture showed down 127/up 0. Generic input is restored and Acoustic Piano selected. Separately fixed focus cleanup resetting the S baseline; source/build are 0.2.12 with 947 pytest, 9 CTest and the new binary probe passing. **Installed/running remains 0.2.11**, pending approval to save/reopen and deploy. Live listening in both modes is still pending. Evidence: `target/pedal-hold-check/`. No hard-coded pedal inversion or guitar/FX routing changes.


### Final pedal release deployment (0.2.12, saved and reopened)

This supersedes the preceding pending-reload status. With user approval, Library was backed up and saved, Bitwig exited normally, and `~/.clap/Chord Lab.clap` was atomically replaced with 0.2.12 before reopening the project. The installed binary passed the complete CLAP probe; SHA-256: `5c02efab99369a046691df44c3d22a84d707da13f6c8976c4d258a9e39ba42d3`.

- Live host check: S stayed green after clicking the host made A red; focusing the plugin and pressing Space restored S red. Momentary pedal XOR behavior is retained without a hard-coded CC64 inversion.
- Both Keystation performance and Transport ports reopened. Spark mono capture feeds Bitwig in1; out1/out2 feed Spark playback. Port numbering changed from out3/out4 on engine restart.
- Ready on `01 Acoustic Piano`, S off, Chord Lab focused, transport stopped. Saved project: `/home/shu/storage/daw/Library/Library.bwproject`.
- 947 pytest, 9 CTest, built/installed binary probes passed; real-host focus/Space checks passed. User listening in both physical pedal modes remains pending; not every sound or hardware listening path was re-audited.
- Main changes: separate computer-key release from sustain reset in `chordlab/midi.jsfx-inc`; focus and held-pedal regressions in `chordlab_clap/sustain_tests.cpp` and `clap_probe.cpp`; CMake version 0.2.12 and bilingual docs. No commit or push; project/runtime backups remain outside Git.
- Evidence and rollback backup: `target/pedal-hold-check/`. The old binary is retained only for rollback, not a parallel product.
