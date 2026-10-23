# Chord Race: Bitwig game mode

[中文](GAME.cn.md) · [Normal mode and deployment history](README.md)

## 0.3.3 chord-choice colors and context acceptance (2026-10-22)

With user approval, Library was saved, Bitwig exited normally, backups created, and 0.3.3 atomically installed before reopening on Workspace 2. SHA-256: `b4ee873cb6aa692a1ebc4c3821ef86aaf2ebe02599592f2a8372b958704c092e`.

- Real Bitwig shows all seven chord capsules. The game target includes degree, symbol, exact bass and octave; the other chords remain visible and unanswered diagram notes remain hidden.
- Both modes use the selected pair's fixed major-scale palette, without rebasing on the relative minor. Top-row key choices keep their existing colors.
- Live G expansion adds 332 px without overlapping sfizz; collapse restores the exact previous 920×703 position and size, normal key and chord. Final G red, S/A green.
- 1348 Python tests, 12 CTests, built/installed CLAP probes, `cargo test` and `cargo clippy` passed. Ten Storage links verified. Presets, routing, Arm, controller and the window-layout service were unchanged.
- Evidence and rollback copies: `target/chordlab-colored-choices/`. This round verifies UI and automated regressions, not a new physical-performance or all-preset listening acceptance. No commit/push; source and deployed files are included in DAW Recovery snapshots.

## 0.3.2 sustain synchronization acceptance (2026-10-22)

0.3.2 is installed after saving, backing up and reloading the real Bitwig Library on Workspace 2. SHA-256: `29cf4c080272ff0462197058f56d3f8ebb5e6147895af52be543a0d72f93ea44`.

- Fix a green S with an out-of-sync downstream receiver: reassert effective CC64 immediately before musical attacks, once per computer chord or per physical attack on its channel. NoteOff, pedal baseline and game rules are unchanged.
- Startup acceptance did not touch S/A: a computer chord held for 50 ms remained sustained after release in Bitwig's output. An equivalent attack with S manually off decayed much sooner; S was then restored. Only Bitwig output was captured, without project recording or Spark input capture.
- The user confirmed both physical MIDI and computer-keyboard sustain without pressing the pedal. Final normal mode: G red, S/A green. Presets, audio settings, controller, Arm and the window-layout service were unchanged.
- 1340 Python tests, 10 CTests, built/installed CLAP probes, `cargo test` and `cargo clippy` passed. The new receiver regression failed on old code and passed after the fix. `live.py --check` verified ten Storage directory links.
- Logs, output audio comparisons, screenshots and previous plugin/project rollback copies: `target/chordlab-sustain-routing/`. No commit/push; deployed files and source are retained in DAW Recovery snapshots.

## Status and boundaries

**Historical 0.3.1 deployment, 2026-10-22.** Bitwig-only Race UI polish: pure black background, cyan keys, yellow current chord, green progression/modulation explanations. Upcoming chords and keys have distinct colors; fixed-size wrapped explanations replace squeezed text. Minimum-height layout preserves the settings area. Colors live in `[game]` in `chordlab/theme.toml`; normal theme, scoring, sounds and routing are unchanged. Standalone is deferred and sound menus cancelled; see [scope history](STANDALONE.md).

0.3.1 SHA-256: `3eeba212ec1beeaedc5dd00605f6eeac63c240fb33fa91231fe16f972efc656a`. With user approval, Library was saved, Bitwig exited normally, CLAP atomically replaced, and Library reopened on Workspace 2. Build, isolated/live screenshots and test evidence are in `target/chordlab-race-polish/`.

2026-10-22: 0.3.0 was backed up and installed in the real CLAP directory. Library was saved and reloaded on Workspace 2. Audio configuration, controllers, and services were not changed. Historical installed SHA-256: `cc336dee7fd61f7bd54d83a09175aa3622c33aff7f1a2d9a9f5feb875dbb046f`. No commit/push. Earlier isolation/deployment-blocker sections are historical; the live acceptance section below supersedes them.

G is an explicit transient mode, not a new host parameter. It defaults red/off. Turning it green adds 332 px, including a gap, to the right of the original 920×703 editor. Start begins; Pause/Resume retains the remaining time; Restart resets scores and randomness. G off restores the previous normal dimensions, key, chord, voicing memory, and controls. Hiding/destroying the editor, host reset, or engine replacement ends the game. Game progress is not persisted.

## Rules

- Both instruments solve the same compact piano voicing. Chord name plus bass octave uniquely identifies it: `Em/G4` means G4–B4–E5, not an arbitrary Em inversion.
- Match exact MIDI pitches, including octaves, arpeggiated or simultaneous. Each instrument collects independently; their hits never pool. First complete collection earns one point and advances. Host event order breaks simultaneous completion ties.
- Repeats earn no extra credit; held notes do not carry into the next target. Release and attack again. Guitar checks monophonic pitch only, not string, fret, or position.
- Default answer time is 10 seconds, adjustable 1–120; timeout reveals and demonstrates the answer for 2 seconds, adjustable 1–10, without awarding a point. Changes apply to the next target. Pause freezes remaining time.
- Keyboard, fretboard, and staff hide answers until correctly played. Hits retain normal scale/chord colors, rims, and halos; wrong pitches do not reveal answers. Timeout reveals the complete target.
- Automatic computer-keyboard chords and normal voicing navigation are blocked during the game to prevent auto-answering. Physical MIDI, guitar detection, and S sustain remain usable. Normal computer controls return when G closes.

## Harmony and voicing

`../chordlab_game/game.rs` embeds UTRP `Progression` with existing `config/simulate.toml` and `config/progressions.toml`. It does not duplicate harmony rules or launch a service. The original engine supplies triads/sevenths, modulation, approaches, and returns; this first version disables extensions and ambient mode. The panel shows the current key/chord, engine reason, and next two targets.

A separate planner selects compact voicings within E2–A5, at most 12 semitones wide. Short segments hold, rise, or fall, favoring common actual pitches and nearby motion; mean-pitch change is at most five semitones. Direction reverses when bounded candidates require it. Visit counts bias sampling away from repeatedly used registers. Limits/weights live in `../chordlab_game/game.toml`, embedded at build time rather than read from the user's working directory.

## MIDI routing

| Channel (1-based) | Purpose |
| --- | --- |
| Input 1–14 | Piano scoring, preserving normal MIDI and pedal routing |
| Input 15 | Guitar scoring/display only; never forwarded as piano notes |
| Input 16 | Existing private computer-control commands; cannot answer |
| Output 16 | Answer demonstration, with independent Note On/Off and CC64 Off |

Keep Library's existing Guitar Frontend channel-2-to-15 Note Receiver mapping. **Route output channel 16 separately to a piano instrument**, preserving other performance channels. Emitting MIDI is not proof that piano routing is installed. This isolated test uses no audio device: it validates pitches/events and timing, not Spark GO tracking accuracy, audible results, or live Bitwig routing.

G off releases only its demonstration channel, not held physical notes or the live pedal. Entering the game releases computer-generated chord ownership; exiting does not replay an already released computer chord. A user's deliberate S change during gameplay is not silently undone.

## Windows and compatibility

- **Inside Bitwig, the existing `../plugin_windows/layout.py` is the sole position owner.** A Bitwig main-window/transient-parent relationship disables plugin-side movement and restoration. G only resizes the editor; the existing policy recalculates the centered group from actual dimensions. No new service. Without the existing policy running, automatic group centering is not guaranteed.
- A complete G cycle can occur between polls, leaving identical dimensions but a host-moved window. Each completed transition replaces its own `utrp-chordlab-layout-<revision>` Sway mark; the policy includes this revision in its signature. User marks are preserved. Deploy the matching layout source together with the CLAP; updating only the plugin is insufficient.
- The policy checks every 0.4 seconds. This guarantees neither frame-perfect transitions nor unlimited screen capacity. Manual moves persist until the next structural change; closing G recalculates the current normal layout instead of restoring stale coordinates. Existing explicit overflow handling remains unchanged.
- **Non-Bitwig isolated/standalone hosts** retain plugin-side Sway arrangement of floating windows in the focused workspace. Same-process neighbors can move; unrelated windows remain fixed. Automatically placed windows restore unless manually moved; insufficient space is reported. Non-Sway hosts do not get automatic neighbor arrangement.
- Sway IPC runs only during G transitions on the UI thread. No global desktop rules were added, and the real desktop layout service was not changed or restarted.
- Stable CLAP ID `org.utrp.chordlab`, 21 parameters, and v3 state format are unchanged. Gameplay does not write normal sliders, voicing memories, or serialized state. Rust planning and Sway IPC never run on the audio thread.

## Validation and reproduction

```sh
cmake --build target/chordlab-clap-build/build -j2
ctest --test-dir target/chordlab-clap-build/build --output-on-failure
python -m pytest -q lib/tools/chordlab/tests lib/tools/chordlab_clap lib/tools/plugin_windows/test_layout.py
cargo test --offline
cargo clippy --offline --all-targets -- -D warnings
cargo test --offline --manifest-path lib/tools/chordlab_game/Cargo.toml
cargo clippy --offline --manifest-path lib/tools/chordlab_game/Cargo.toml --all-targets -- -D warnings
```

- 569 Python tests and 10 CTest entries. Game tests execute production JSFX and its C++ bridge.
- Checks cover independent scores, wrong octaves, repeated/held notes, pause, sample-accurate deadline, demo cleanup, rapid toggles, host reset, unchanged serialization, reload default-off, and instance isolation.
- `game_tests CURRENT.jsfx ORIGINAL.jsfx` compares post-toggle normal MIDI byte-for-byte with the original engine, not just another updated instance.
- Rust uses eight seeds × 1500 targets: reproducibility, compactness, movement bounds, and all 42 E2–A5 pitches visited for each seed. This is tested long-run coverage, not a guarantee for every short session.
- Original CLAP probe checks 12 sample-rate/block-size combinations, 21 parameters, held notes/pedals, old state, Guitar/Piano switching, and independent instance lifecycle.
- `game_preview plugin.clap midi-in.txt midi-out.txt` is a wall-clock-paced native CLAP host with no audio devices. Input lines contain decimal `increasing_serial status note velocity`. Use only in isolated Sway; synthetic MIDI is not a real-guitar acceptance test.
- Screenshots, logs, and before/after layout JSON are archived under `target/chordlab-game-validation/` (not Git). Before live installation: save Library, verify ch16 piano demonstration and Spark monophonic scoring, check existing window-service interactions, then update recovery records/snapshots through `../daw_backup/`.

- Layout follow-up: 368 layout tests plus 569 plugin Python tests (937 total), and strict mypy passed. Actual candidate CLAP with a mock Bitwig parent/sfizz and updated policy in isolated Sway passed 20 full cycles, 20 rapid toggles, drag/close and stability checks. User marks survived and exactly one revision remained. This is not real Bitwig/audio acceptance.

## Multi-window follow-up and deployment blocker — 2026-10-22

- Both game/normal widths now cover all existing instrument/effect opening orders: 708 layout tests, 1319 Python tests including plugin, Library controller and recovery utilities. Ten CTest entries, original-engine normal MIDI comparison, and game-crate cargo test/clippy passed again.
- Five windows in isolated Sway (candidate Chord Lab, mock sfizz, two mock FX and mock reverb) passed ten transitions: no overlap, within available bounds, 16 px spacing and stable closure. Evidence: `target/chordlab-game-validation/multi-game-*.png/json`.
- The user authorized saving and reloading, but no real Bitwig/Sway desktop session or PipeWire input/output endpoints are currently accessible; Spark GO/U Audio were not found, though ALSA lists other onboard/USB devices. Installed plugin and Library remain unchanged; do not claim live saving/reloading or human listening acceptance. Resume ch16 demo routing and Spark detection acceptance when the real session is available.

## Live Bitwig acceptance — 2026-10-22 (supersedes deployment blockers)

- Real Sway output is 3440×1440; Library runs on Workspace 2 with Keystation 61 MK3 and Spark GO connected. Existing routes are Spark mono → Bitwig in1 and Bitwig out1/2 → Spark stereo. Audio configuration was not changed.
- A Storage recovery snapshot preceded atomic CLAP 0.3.0 installation. Bitwig was not running at first launch; Library was subsequently saved, normally exited, and reopened for reload acceptance. No recording or controller changes were enabled.
- Current sounds remain `Basic Keys / 02 Soft Piano (sfizz)` and `AG - 01 Glass Air`. Timeout demo ch16 actually triggered sfizz (4 voices in the screenshot). A 17-second Bitwig stereo-output diagnostic capture peaked at -15.82 dBFS with no NaN/Inf; no microphone or Beat Lab recording was enabled. User playing is mixed into this capture, so it is not an isolated-instrument measurement.
- The real game showed Guitar 2 points, and the user confirmed actual guitar playing. A separate post-reload physical MIDI round showed Piano 1 point. Evidence includes `demo-real.png`, `score-final.png`, and the user's confirmation. Automated tests separately cover independent hit collections, wrong octaves, held notes, demo cleanup, and state isolation.
- All 20 real Bitwig transitions passed screen bounds, non-overlap, 16 px spacing, centered grouping, and a single revision mark. Normal editor 920×703, game 1252×703, sfizz 775×515. The user confirmed both physical MIDI and computer-keyboard sound after exiting the game.
- Standalone was actually launched with Bitwig closed, but contains no instrument host: **standalone playback and the in-plugin sound selector remain unfinished**. See [standalone/catalog status](STANDALONE.md). The test application was closed and Library restored; startup G red, S/A green, normal dimensions, and Workspace 2 were verified.
- 1437 Python tests, 10 Chord Lab CTests, and 2 Guitar Frontend CTests pass. The installed CLAP ABI/lifecycle probe, root Rust test/clippy, and game crate's 2 tests/clippy pass. New catalog strict typing passes. `live.py --check` verifies all 10 live Storage directory links.
- Physical MIDI scoring temporarily used 30 seconds; cleanup restores 10/2 seconds, closes G, and saves Library with recording off. Screenshots, capture, logs, current DAWproject export, and catalog are under ignored `target/chordlab-live-game/`.
- Recovery inventory now records 0.3.0 and optionally includes the existing layout-service drop-in. No service was created. Final `lib/tools/daw_backup/snapshot.py` recovery output is referenced by `~/storage/daw/Recovery/LATEST`. Source remains uncommitted/unpushed.

## 0.3.1 verification — 2026-10-22

- Passed 1,340 related Python tests, 10 CTests, CLAP probe (legacy states, independent instances, 12 sample-rate/block combinations), root `cargo test --offline`, and `cargo clippy --offline --all-targets -- -D warnings`. This is not an all-domain repository acceptance claim.
- Audio-free isolated Sway checked default and minimum heights. Actual Bitwig panel background pixels are `(0,0,0)`; live screenshot: `target/chordlab-race-polish/live-game.png`.
- 20 real Bitwig transitions passed bounds, separation, 16 px gap, centered group and bounded revision-mark checks. After G off, normal screenshots differ only in A's focus indicator (finally green); all other normal-mode pixels match. Restored 920×703, G red, S/A green.
- PipeWire Spark/MIDI/Bitwig links exactly match the previous acceptance. No new user-play test was requested this round; earlier live playing/scoring evidence remains historical, not a new UI-based sound confirmation.
- Pre-update recovery: `20261023T025208.763013Z`. Post-update snapshot: `target/chordlab-race-polish/recovery.txt` / Storage `Recovery/LATEST`. No controller, audio configuration or service changes; no commit/push.
