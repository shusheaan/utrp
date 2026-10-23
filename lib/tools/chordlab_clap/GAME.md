# Chord Race: Bitwig game mode

[中文](GAME.cn.md) · [Normal mode and deployment history](README.md)

## 0.3.5: live Library acceptance and panel-local countdown (2026-10-23)

This supersedes older candidate-only deployment statements. 0.3.5 is installed at the existing Storage-backed `~/.clap/Chord Lab.clap`; no new audio service or controller changes.

- The four-pixel countdown now belongs to the top of the black GamePanel, not the full editor. Closing G hides it along with the panel; the normal music canvas is unchanged.
- Real Workspace 2 / Library / Spark I/O: the user confirmed physical MIDI, computer A and guitar sound. Released computer notes measured approximately −45.9 dBFS RMS with startup Sustain and −74.4 with Sustain off; S/A restored on.
- Low-level synthesized A4/C#5/D#5/F#5 through the real Guitar Frontend input path completed D#m7b5/A4 and awarded guitar 67 points. This is an end-to-end synthetic-pitch check, not a claim about human guitar recognition accuracy.
- A real timeout awarded no points, revealed all notes and played four sfizz voices. The Bitwig-only output capture peaked around −17.1 dBFS. DAW and Beat Lab recording stayed off. Not every library preset was retested.
- Evidence: `target/live-acceptance-20261023/`. Normal 920×703 and expanded 1212×703 windows recenter together with the sound editor; final layout/countdown screenshots are stored there.

### Statistics: current behavior and proposed persistence

The game already balances reachable destination keys by successful completions within the current run, after successful coverage of all seven backbone degrees, subject to modulation probability and return tolerance. Restart/closing the editor clears these counts. `Progression.key_practice` counts generator consumption and includes committed lookahead in the plugin; it must not be presented as actual user practice.

A new production-planner regression uses three committed groups, seed 20261023, 50% modulation, and one timeout per eleven exercises. Across 4,800 actual exercises it visits all 24 major/minor keys and 574 key/chord identities, with 171–206 successes per key. It checks ordered/duplicate completion, actual-only audit counting and successful-degree gating. These are test audit statistics, not a newly shipped statistics UI or persistent store.

Proposed records: key pitch class/mode, chord root/quality/degree, approach kind, inversion/exact notes, winner, speed score, answer time and timeout. Keep piano/guitar separate; exclude pause/demo time and never count previews. Balance mainly by successful chord count, using presented counts/time diagnostically rather than reducing practice of difficult keys merely because they take longer.

Proposed storage is per-session JSONL under `~/storage/daw/UserData/ChordLab/training/`, separate from TOML configuration. Unique session IDs/files avoid multi-instance overwrites and permit rebuilding summaries. This directory and persistence are **not implemented in this turn**; implementation must also extend recovery coverage. Global balancing would seed starting-key selection from history and continue respecting reachable harmonic routes, not force exact equality by arbitrary jumps.

## 0.3.4 candidate: single-column stairs and wheel controls (2026-10-23)

This section supersedes the earlier wide, horizontal capsule layout below. The user's installed plugin and real Library remain untouched.

- The panel shrinks from 480 to **280 px**: default editor 1212×703, normal mode still 920×703. Default chord/key capsules are 115×23 / 57×23, sharing left-side dimensions and fitted typography. JUCE uses point sizing rather than applying the LICE backend correction twice.
- Three committed destination groups use a **single-column staircase**: one actual chord per line, 16 px indentation per step, reset at group boundaries. Completed steps remain hollow in place. At small heights only the progression scrolls; scores/settings cannot overlap it.
- Temporary approaches have gray fill/outline and a 6 px destination-relative degree-color dot; completion leaves a gray hollow capsule and the dot. Other chromatic chords are also neutral rather than falsely claiming diatonic membership. Real diatonic destinations retain the fixed relative-major palette.
- Future key: white fill/gray text; current key: gray fill/white text. The method below the key comes from the committed route: shared seventh with old/new degrees, diminished pivot, or destination V7. The destination mode determines I/i. Repeated keys are omitted.
- Top scores show piano/guitar totals only, no 0/4. Successful replay briefly shows `✓ +speed award`, not a new fixed-one-point rule. Harmony, NOW/NEXT/THEN, and textual countdown are removed.
- A 4 px shrinking green bar spans the whole editor. Pause freezes it; demo uses its own duration. Current durations are latched, so wheel changes cannot jump the active bar.
- Bottom settings occupy 178 px. Play, Demo, and Modulation chance each have one compact label/value row and wheel input without +/- buttons: steps 1 s / 1 s / 5%, bounds 1–120 s / 1–10 s / 0–100%. Probability, direction, and approaches still apply on restart. Approach text is smaller, with deliberate central whitespace.

The production Rust planner + JSFX bridge passed 180 rounds: piano 4120, guitar 4140, 16 timeouts, 56 approach events, and 7 modulations. Assertions cover every speed award, separate cumulative totals, no replay double-credit, and successful seven-degree coverage before modulation. Live CLAP screenshot evidence is stored separately under `target/chordlab-stairs-ui/evidence/`; synthetic MIDI is not physical-guitar or listening acceptance.

The live run also exposed a modulation-arrow rendering crash caused by using JUCE ASCII string constructors for UTF-8. A new regression exited 139 before the fix and passed after explicit `String::fromUTF8`, covering four method descriptions. Failed-run frames are archived separately and excluded from acceptance. No commit/push.

Additional acceptance: after the UTF-8 fix, isolated CLAP completed 75 alternating synthetic-MIDI rounds, ending at piano 3588 / guitar 3505. Screenshots cover local ii–V, tritone substitutions, shared-seventh modulation, future white keys and current gray keys. The final candidate passed Start/Pause and collapse/expand in a real temporary Bitwig project: 1212×703 centered at x=354; 920×703 restored at x=500. Normal musical rendering pixels matched. 573 related Python tests, 12 CTest cases, root/game Rust tests and Clippy, and the final CLAP probe passed. Installed 0.3.3 SHA is unchanged; temporary-HOME installation is neither production deployment nor listening acceptance.

## 0.3.4 candidate: aligned columns and retained progress (2026-10-23 UI draft)

This follow-up changes only game-panel layout/progress presentation, not harmony generation, scoring, replay, normal input/rendering or the user's Library. It is not deployed to the real home plugin directory. Earlier 320/332 px figures below are historical: the new game panel is 480 px, adding 492 px including spacing. The left area retains its normal width; G off restores the previous size.

- Fixed key column plus three equal chord slots. Single chords no longer stretch across a row. Repeated keys leave their column blank without shifting chords. Future new keys are white; the current key is black.
- Current: bright fill, white rim, `PLAY`. Upcoming: dimmed degree colors. Success: black fill, colored outline, `DONE`. Timeout: `MISSED` with an error-colored outline, never presented as success.
- Completed/passed steps stay in their slots within an approach/resolution group, preventing horizontal jumps. Move to the next row only after the whole group ends. This is a bounded active-chain trail, not unlimited history; reset/exit/new group clears it.
- The upper area shows progression, seconds and separate scores (with hits/current award). Coverage, question/miss counts and extra explanatory text are hidden; the seven-degree modulation gate still applies internally. Existing settings remain below, aligned to the wider panel. Timing/difficulty is unchanged and no unimplemented technique switches are exposed.

Validation/evidence: start/pause and layout verified in isolated real Bitwig 6.1.4. Expansion is 1412×703; collapse restores 920×703, with staff/keyboard/fretboard/capsule pixels identical to the pre-game image. Synthetic MIDI in the isolated CLAP host verified a completed approach staying in place while the next capsule highlights. Root Rust 123 passed (3 ignored), six game-crate tests, both Clippy runs, 1,281 related Python tests, 12 CTests, CLAP probe, normal-MIDI baseline comparison and real painting at three heights passed. A new generated-sequence assertion limits each group to three slots. Screenshots/logs/hashes: `target/chordlab-aligned-columns/evidence/`; `columns-*.png` are explicit paint fixtures, other runtime captures come from isolated hosts. No physical listening acceptance; installed 0.3.3 hash remains unchanged. No commit/push.

### Harmony-study practice: captured scope, not yet implemented

The user requested all five topics. This iteration delivers the UI first. **Dedicated exercises below remain incomplete**, even where the engine has a related behavior:

- [ ] Common-tone Harmony: extend the existing absolute-common-pitch reward into explicit targets/constraints and checks; distinguish a preference from actual retention. Existing foundation: `common_weight` in `chordlab_game/game.rs`.
- [ ] Chromatic Voice Leading: constrain named voices to semitone motion with correspondence tracking; nearby motion or chromatic chords alone are not sufficient acceptance criteria.
- [ ] Planing: add structure/spacing-preserving movement and boundary tests; distinguish exact chromatic transposition from diatonic movement, rather than reusing mean-register Rise/Fall.
- [ ] Modal Interchange: annotate same-tonic borrowing and source mode without declaring modulation. The underlying engine has an `extensions`-gated parallel-minor iv branch, disabled in game practice and producing a triad; this is not a ready all-seventh exercise.
- [ ] Pedal Point / Upper Structures: specify fixed-bass and upper-chord targets separately. First reconcile sustained bass with the current compact four-note seventh/single-hand constraints, and determine whether the bass is played or supplied by accompaniment. Do not silently discard bass or change answer cardinality.

Each implementation needs generation invariants, exact pitches, readable labels and committed-preview consistency tests. No inactive menus are added now. Named genres describe use cases, not mutually exclusive categories for these techniques.

## 0.3.4 candidate: grouped capsules and completion replay (2026-10-23 follow-up)

**UI verified in a disposable project in real Bitwig 6.1.4 under isolated Sway; the user's installed plugin and Library remain unchanged.** No physical audio device was used. Temporary processes supply a silent audio clock, without installing a service or changing user audio, controllers, sounds or layout services. The next section records the earlier policy milestone.

- NOW / NEXT / THEN are three committed **harmonic destination groups**, including each approach and its resolution, e.g. `ii → V → iii`. The first two labels are relative to iii; the destination retains its home-key iii label. Each chord remains a separate question, and only the currently played capsule has a white outline. FIFO previews are never regenerated after display. Three groups contain at most nine actual events; unlocking modulation does not replace committed previews.
- The current key is black with white text. A future group entering another key gets a white badge with black text, turning black when current; consecutive unchanged keys omit repeated badges. Destination colors reuse the left panel's fixed relative-major palette. **Local approaches are the exception**, colored relative to their destination root: ii green, V orange, actual tritone bII green and related bvi blue (not every dominant-function chord is orange). Spelled bass/octave and chord-relative bass degree occupy a second line.
- Both success and timeout reveal all target notes and emit the full demonstration chord, default two seconds, before advancing. Piano/guitar totals are separate; only the first instrument independently collecting all four pitches scores. Replay does not accept another winner. MIDI event validation does not imply audible output or physical-device acceptance.
- New speed score: `ceil(100 * answer_time_remaining / answer_time_limit)`, clamped to 1–100 for success, zero for timeout. Pauses and replay do not consume answering time. The terminal version used completion-rate statistics, not this speed formula; this is a new rule, not restoration of an existing algorithm.
- Lower controls remain Start/Restart, Pause/Resume, Play/Demo seconds, modulation chance, register direction and approach toggle; no extra advanced settings. Setting application boundaries remain as documented below.
- Fixed a real JUCE paint crash caused by non-ASCII text using an ASCII String constructor: arrows and half-diminished symbols explicitly use `String::fromUTF8`. A real paint regression covers idle, three groups/nine capsules, pause/replay, three heights and black/white key-badge pixels.

Validation: root Rust 123 passed/3 ignored plus Clippy; six game-crate tests plus Clippy; 1,340 Python tests; 12 CTests; CLAP lifecycle/state/MIDI probe; isolated JUCE paint regression. Real Bitwig exercised start, pause/resume, timeout reveal/replay and G expansion/collapse. G off restored 920×703; staff, keyboards, fretboards and chord-capsule pixels were identical to the pre-game image. Normal-mode MIDI also matched the pre-follow-up source snapshot. Synthetic MIDI in the isolated native CLAP host confirmed success reveal/replay and speed credit (90 points for roughly one second), plus the white future G minor badge becoming black/current after Gb major. These checks do not replace physical MIDI/guitar, sound routing or listening acceptance.

Evidence: `target/chordlab-game-capsules/`. No commit/push. This follow-up does not change normal-mode rendering/input rules; the previous milestone's bass-degree annotations remain.

## 0.3.4 candidate: seventh-chord practice policy (2026-10-23)

**Source/build candidate only; not installed or accepted in real Bitwig yet.** No Library, sound, routing, controller or window-service changes. Styles and standalone remain deferred.

- The plugin opts into a separate practice policy; the terminal simulator keeps its existing defaults. Start at a random position in the original closed degree cycle (do not double-weight its repeated closing I). All game targets, approaches, pivots and arrivals are complete seventh chords. Shared-chord modulation requires a shared seventh, not merely a shared triad.
- Unlock automatic modulation only after successful completion of all seven backbone degrees in this visit to the key. Either instrument can supply each completed chord; the two instruments cannot combine partial answers. Timeouts, previews and approaches do not fill the seven-degree checklist. An arrival tonic can fill I. This is degree coverage, not every inversion or every chromatic chord. Revisiting a key resets the checklist.
- After coverage, check at the next safe planning boundary, then every four eligible backbone opportunities (configurable). Default chance is 50%; 0% disables automatic modulation. Never interrupt a committed approach/resolution. Two upcoming targets are immutable, so unlocking does not replace an already visible chord. The old 40-event balance tolerance is **not** a waiting requirement; it remains only in the inherited return-destination eligibility rule.
- Destination balance uses successful target counts in this game, not generated previews. Among reachable keys, prefer the least practised, with random ties. The inherited 20% return preference may choose the previous key if eligible, but does not bypass coverage; consecutive returns are suppressed. Route choices remain dominant, shared seventh and diminished seventh, selected from available methods, not fixed equal unconditional probabilities.
- Voicings are compact, four-note, single-hand inversions within E2–A5, span at most 12 semitones. Fixed chord symbol plus spelled bass/octave uniquely identifies this restricted voicing family (not arbitrary open, rootless or doubled jazz voicings). Capsules now annotate the **bass's chord-relative degree**, e.g. `ii Dm7/F3(b3)`: root D, bass F, minor third. Normal mode retains its triads/sevenths/ninths and guitar choices.
- Register phrases last 4–8 targets. Mixed samples Hold/Rise/Fall using configurable weights (currently 1:1:1). Minimize sorted voice movement, reward common absolute pitches, discourage overused pitches and add bounded jitter. Rise/Fall constrain the mean pitch direction and reverse at the reachable boundary; mean-pitch step is at most five semitones. These are soft common-tone preferences, not a promise to hold every shared pitch or a five-semitone limit on each individual voice.
- Top: current key/time, NOW and NEXT +1/+2 cards (degree, chord/bass, action, key route), seven-degree coverage, scores and presented count. Bottom: Start/Restart, Pause/Resume, answer/demo seconds, modulation chance, register direction and approach toggle. Time changes affect the next target; other panel settings apply on Restart. Panel settings are session-local, not new saved host parameters.
- Advanced defaults remain build-time TOML: `chordlab_game/game.toml` for range, direction weights, phrase length, cost weights and check interval; `config/simulate.toml` for four approach probabilities (10%/5%/10%/5%), return and route pool. These are conditional approach choices, not percentages of all emitted targets. Editing TOML requires rebuilding the plugin. Separate advanced UI controls are not implemented yet.

Validation: root Rust suite and Clippy, four game-crate tests and Clippy, 1,340 related Python tests, 12 CTests, and built CLAP lifecycle/state/MIDI probe passed. New regressions cover missing-degree/timeout lockout, random starts, seven-success gating before a full lap, all-seventh targets, FIFO acknowledgements and committed previews. The final candidate received 60 alternating synthetic piano/guitar MIDI batches in the isolated host: the UI showed P30/G30, Miss0 and target 61, with a shared-seventh modulation visibly announced in advance. Default/minimum layouts and G-off restoration passed. Synthetic input is not real-instrument acceptance. Audio-free isolated Sway evidence is in `target/chordlab-seventh-practice/`; this is not physical MIDI/guitar or real-Bitwig listening acceptance. No commit or push.

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
- Match exact MIDI pitches, including octaves, arpeggiated or simultaneous. Each instrument collects independently; their hits never pool. First complete collection earns speed credit and advances after full replay (formula in the latest candidate section above). Host event order breaks simultaneous completion ties.
- Repeats earn no extra credit; held notes do not carry into the next target. Release and attack again. Guitar checks monophonic pitch only, not string, fret, or position.
- Default answer time is 10 seconds, adjustable 1–120; timeout reveals and demonstrates the answer for 2 seconds, adjustable 1–10, without awarding a point. Changes apply to the next target. Pause freezes remaining time.
- Keyboard, fretboard, and staff hide answers until correctly played. Hits retain normal scale/chord colors, rims, and halos; wrong pitches do not reveal answers. Success and timeout both reveal the complete target.
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
