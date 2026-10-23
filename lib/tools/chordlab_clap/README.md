> **0.3.3 installed in real Bitwig on 2026-10-22**: see [game mode and live validation](GAME.md). [Standalone playback](STANDALONE.md) is deferred; sound menus are cancelled; normal-mode documentation and installation history follow.

# Chord Lab CLAP 0.2.14

## Fixed major-key colors and game chord choices (0.3.3, 2026-10-22)

- Color only the second-row chord capsules; top-row key pairs such as `Am/C` are unchanged. Reuse note fills and text colors, with saturated fill and a white rim for the current target.
- Colors are fixed to the selected pair's major scale, never rebased on the current chord or relative minor. For example, A remains C major's blue sixth under `Am/C`, not a new red tonic. The game's upper scale diagram uses that same fixed major palette; lower chord-role note colors are unchanged.
- Keep seven contextual chord choices visible in game mode. The target includes its degree, symbol, exact bass and octave; borrowed/altered chords include labels such as `bII`. Other capsules show current-scale triad context, not invented future voicings.
- Game choices are read-only. Scoring, deadlines, hidden unanswered notes, revealed hits, normal selection and voicing memories remain unchanged. G off restores normal mode.
- New real-JSFX label and LICE pixel regressions cover 12 keys × major/minor × 7 roots, inversion/altered degrees, fills/outlines at three widths, locked game clicks and normal interaction. 1348 Python tests, 12 CTests, CLAP probe, `cargo test` and `cargo clippy` passed. Isolated Sway screenshots: `target/chordlab-colored-choices/`; see GAME for live deployment status.


## Sustain receiver synchronization (0.3.2, 2026-10-22)

- Fix normal-mode physical MIDI and computer chords releasing immediately despite a green S when the downstream instrument has not received effective CC64. A startup-only message cannot cover late loading, reactivation or a downstream controller reset.
- Reassert effective per-channel CC64 before each physical NoteOn and once before each computer chord attack, at the same sample offset and before notes. NoteOff remains balanced and unmodified; no periodic polling.
- Preserve manual S Off, temporary pedal inversion of the baseline, fourteen musical channels and analysis/command isolation. Normal-mode voicing, UI and focus logic are unchanged, as are presets, routing, Arm and services.
- The new receiver-reset regression fails on the old code and passes with the fix, covering both baselines, both pedal states, fourteen channels and computer chords. Evidence: `target/chordlab-sustain-routing/`.


## Default Sustain and startup Focus (2026-10-21)

- New or reloaded instances start with Sustain On, including old projects saved Off. The first audio block clears stale downstream sustain with CC64 Off, then enables all 14 musical channels. Saved commands are not replayed; initial host transport delivery is not mistaken for an actual transport stop.
- Computer keyboard capture starts enabled. The editor acquires focus once its native parent is viewable, including reopening. It does not repeatedly reclaim focus after the user leaves; manually disabling A remains effective in that editor. Hardware MIDI is independent of GUI focus.
- Space/S can still turn Sustain off. Losing focus or hiding/closing the editor preserves the current baseline. Actual transport Stop and emergency cleanup still release sustain. Reopening the GUI alone does not reset a manual Sustain choice.
- Default 920×703 size, twenty frets and upper-position dots, 21 parameters and v3 state remain unchanged. No new services or changes to audio routing, levels, Arm or Library exclusivity.

Evidence: `target/chordlab-startup/`. Added real CLAP fresh/restored startup tests and X11 delayed-map, no-focus-stealing, close/recreate tests. Final physical keyboard/speaker listening remains user confirmation.


Acceptance: 975 Python tests, nine CTests, and built/installed CLAP probes passed. The additional `clap_probe <plugin> --focus` ran in isolated rootful Xwayland to verify delayed native mapping and one-shot focus. Rootless Sway redirects focus for the probe's unmanaged windows and is unsuitable for that isolated check. The temporary server did not listen on the network and was terminated afterward; JUCE's WM atom names were pre-registered there.

Bitwig Library was saved, backed up and restarted. Its Workspace 2 editor opened at 920×703 with both S/A green. Without clicking the editor, a chord key sent to its existing native focus produced four sfizz voices; release/cleanup restored Sustain On. XTest did not deliver effective keys in this rootless session; the successful evidence uses XSendEvent, not claimed physical keyboard acceptance.
Installed SHA-256: `39492f9bdf064aaa50aed63cc9df3bf695e847e23866edeb085f3e0e4c65a7ac`.

## Earlier releases

# Chord Lab CLAP 0.2.13

> 2026-10-21 recurrence fix: [native map-time rules](../plugin_windows/README.md) remove the initial tiling/floating size race. New shared/guitar editors open at 920×703. The earlier unchanged-window-policy note below describes the temporary repair. Plugin binary and twenty-fret behavior are unchanged.


## Twenty frets and upper positions (2026-10-21)

- Both boards use `guitar.toml`'s `max_fret = 20`, retaining the default 920×703 editor and existing font/note sizes rather than enlarging the window.
- Seventh-chord index candidates repeat every 12 frets. The anchor limit grows from 14 to 18, leaving two higher frets for the complete three-fret region. Coverage-based adjacent-candidate filtering remains; not every fret is marked.
- In Guitar mode, the chord board's upper edge shows hollow alternatives and the filled current anchor. Upper positions share the catalog used by H/L navigation, MIDI output and v3 state restoration. Piano mode does not show hand-position dots.
- The live window had reached its permitted maximum of 1636×1220 and was restored through the window manager. Plugin zoom, default dimensions and global window policy are unchanged; dimensions alone do not establish what triggered enlargement.
- Stable CLAP ID, 21 parameters and v3 state format are unchanged. Older valid anchors remain readable and resolve to the nearest current catalog entry.

Validation evidence: `target/chordlab-twenty-frets/`, including board bounds, octave candidates in all 12 keys, held navigation and persistence of anchor 18 with a sounding twentieth-fret pitch.

Acceptance: 569 Python tests, nine CTests and built/installed CLAP probes passed, plus 396 related layout/controller/backup regressions. Library was saved, backed up and restarted; live inspection confirmed 920×703, twenty frets and upper-position dots.

## History

# Chord Lab CLAP 0.2.12

## Momentary pedal and focus fix (2026-10-18)

- Physical capture showed reversed polarity: down CC64=0, up=127. After the user restarted Keystation with the pedal released, capture showed down=127/up=0. No hard-coded inversion or first-event polarity guessing was added.
- Space/S chooses the pedal-up baseline; holding the pedal temporarily inverts it and releasing restores it. S displays only the baseline. Repeated CC64 does not toggle; a four-second event-free hold remains down.
- Separate fix: losing focus or closing/hiding the editor now releases computer keys without resetting the sustain baseline. Hardware note ownership and pedal state remain intact. Released computer notes still follow active sustain rather than being forcibly silenced.
- Transport stop, real musical-channel emergency cleanup/reset and plugin reload retain safety reset behavior. This is not cross-restart sustain persistence.
- Sustain off means normal note release, not a volume mute. Physically held notes are not cut off by the pedal.

Evidence: `target/pedal-hold-check/`. The new focus regression fails against the old engine and passes after the fix; the real CLAP probe also checks momentary behavior after focus cleanup. Captured CC64 is not listening acceptance for every instrument.

## Historical notes (0.2.12 supersedes focus reset behavior below)

# Chord Lab CLAP 0.2.11

## 2026-10-18: pedal temporarily inverts the sustain baseline

- S displays the pedal-up baseline, not the physical pedal: red means up/off and down/on; green means up/on and down/off. Space or clicking S changes the baseline.
- CC64 is tracked independently on 14 musical channels; effective sustain is baseline XOR pedal-down. Mid-pedal baseline changes are immediate. Repeated CC never toggles S. Threshold is 64; this is not continuous half-pedaling.
- Pedal changes emit CC64 only, not note-off or volume-mute commands. Held hardware/computer notes survive. Display channel 15 and command channel 16 cannot change pedal state.
- Controller resets clear the relevant transient pedal state. Existing focus/close cleanup of the computer baseline remains. Release/repress after reloading. Tooltip updated; parameter count, names/IDs and project state format remain compatible.
- Physical polarity must produce up=0/down=127; the plugin does not guess polarity or learn a baseline from an arbitrary last event.

Evidence: `target/pedal-baseline/`. Engine coverage adds 224 threshold/channel cases plus held toggles, note ownership, display isolation and resets. The CLAP probe independently checks actual binary pedal messages. Physical listening confirmation is still required after deployment.

## Previous releases

# Chord Lab CLAP 0.2.10

## 2026-10-18: more outer whitespace

- Add configurable outer padding (`theme.toml`, `[editor]`: `padding_x = 18`, `padding_y = 10`). Default window grows from 884×683 to 920×703; the embedded 884×683 canvas is unchanged. Side margins become 36 px, top margin 20 px, and bottom whitespace gains 10 px.
- Both resize limits gain the same padding, preserving the previous canvas size range. S/A hit targets and error text follow the canvas offset, keeping alignment with the key rail.
- No scaling of fonts, capsules, note markers or diagrams. S/A circle geometry, all MIDI behavior, parameters and saved-state format remain unchanged.

Validation and deployment evidence: `target/editor-padding/` (backups, Python/CTest logs, CLAP probe, before/after screenshots).

## Earlier release notes

# Chord Lab CLAP 0.2.9

## 2026-10-18: inset S/A indicators

- Keep S and A as two separate circles. Their radius now matches the selected small capsule, not the outer rail: `(29 - 2*3 - 1)/2 = 11 px`.
- Both use the same `choices.inset` from TOML; the JUCE header exports it as `selection_inset`. Each circle has 3.5 px geometric padding inside its existing 29 px click target, leaving 7 px between the circles.
- Outer rail, text, red/green colours, hit targets and all MIDI/control behaviour are unchanged.

Validation: 540 Python tests, including shared inset values 2/3/4 and invalid-value rejection; full CTest and installed CLAP checks recorded under `target/state-pill-inset/`. Previous plugin/project and before/after screenshots are retained there.

## Earlier release notes

# Chord Lab CLAP 0.2.8

## 2026-10-18: retrigger shared physical notes

- Every hardware Note On on channels 1–14 now triggers an attack, including pitches held by computer chords. Original velocity, channel and sample offset are preserved.
- A shared/repeated pitch sends Note Off then Note On at the same sample offset, rather than suppressing the attack or stacking unmatched instrument voices. Computer chords also rearticulate hardware-held pitches.
- Input ownership remains separate: releasing either source cannot cut the other held source; the final release stops the shared pitch. This is shared same-channel ownership, not two independent sustained voices.
- Guitar analysis on channel 15 stays display-only. Controls, UI, parameters and saved-state format are unchanged.

Validation: the new regression failed on the old engine, then passed 1,792 physical pitch/channel cases and 2,016 mixed-input cases (12 keys, seven degrees, three chord types, both voicing modes, both input/release orders). All eight CTests, 532 Python tests and the binary CLAP probe passed. The probe checks exact attack velocity/timing, sustain, both release orders and guitar isolation. Evidence and pre-update backups: `target/midi-retrigger/`.

## Earlier release notes

# Chord Lab CLAP 0.2.7

## 2026-10-18: pill edge polish

- Correct LICE's inclusive circle-pixel bounds: use `(height-1)/2`, integer centres and the matching right endpoint. No lower/right protrusion from the previous `height/2` geometry.
- Replace the detached saved-state dot with ` *` beside the chord text, included in shared font measurement and centring.
- Draw S/A as separate red/green circles with white letters. Half-pixel inset matches the rail radius and prevents overlapping neighbours.
- Keyboard, MIDI, instruments and monophonic guitar detection are unchanged.

Validation: 532 Python tests, seven CTests and the installed-binary CLAP probe passed. New `capsule_pixels` runs the actual JSFX/LICE renderer for 23/29 px heights, circular and elongated shapes; it verifies no lit pixels outside bounds and exact vertical/horizontal reflection symmetry. Backups and deployment screenshots: `target/pill-polish/`.

## Earlier release notes

# Chord Lab CLAP 0.2.6

## 2026-10-18: continuous pill selection rails

- Both choice rows are 29 px tall and share one font size (base 10 × font_scale). At narrow widths both rows shrink together; selection no longer changes font weight or size.
- Continuous round-ended tracks contain inset selection pills with 3 px vertical padding. Hit regions remain contiguous. S/A keep square bounding regions; A closes the right rounded end of the top rail.
- Tiny white dots indicate the `saved[degree*4]` memory flag. Changing chord type or piano inversion/register saves automatically; Enter also sets it. They are not sound indicators or proof that a value differs from default. Guitar position memory is separate.
- MIDI, guitar positions, H/L, J/K, Enter, Space, focus, 21 parameters and state compatibility are unchanged.
- Guitar Frontend is now mono-only 0.2.1; see [mono wrap-up](../guitar_frontend/MONO_ONLY.md).

Validation: 631 pytest cases, six Chord Lab CTests and installed-binary CLAP probe passed. Bitwig visual checks, first/last/middle selection and computer-key press/release checked. Evidence/backups: `target/mono-pill-wrapup/`.

## Earlier release notes

# Chord Lab CLAP 0.2.5

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

## Current update: Enter reset and more colorful idle notes

- **Enter** resets only the current chord in the current mode: Piano uses root position with MIDI center 60; Guitar resolves to the available anchor nearest the configured default fret 11.
  Key, degree, triad/seventh/ninth type, other degrees, and the other mode's memory are preserved. Held chords update immediately; idle reset stores without auditioning.
  Reset is remembered automatically; cross-session persistence still requires saving the DAW project. Requires focused, active capture and no modifier combination. Space remains Sustain.
- Idle notes now retain 80% of the role color instead of 40%, reducing neutral gray and slightly increasing brightness. Active fills are unchanged.
  Labels remain white and active in-key notes retain exterior white rims. Halo width increases from 2.5 to 3.5 px, extending 4.3 px including the rim; core marker/font size are unchanged.
  Out-of-key physical MIDI remains gray with a gray halo; input semantics are unchanged.

562 pytest cases, 6 CTest groups, and the real CLAP probe pass. New reset checks cover 12 keys × 7 degrees × 3 types × 2 modes (504 cases),
including held/idle reset, other-degree/mode isolation, and save/load. Keyboard tests cover Enter repeat suppression and preheld-key focus-loss blocking.
The test host now explicitly uses stopped transport so YSFX's default playing state cannot silently prevent the 12-key matrix from changing key.
Bitwig checks in both modes confirm that H then Enter restores a pixel-identical default diagram. The shared CLAP is installed;
Library was reopened from its pre-test saved state with focus restored and remains byte-identical to the backup. Hardware, all timbres, and REAPER were not retested.
Evidence: `target/chordlab-enter-reset/`. Main changes: `keyboard-map.txt`, `midi.jsfx-inc`, `theme.toml`, generator, and corresponding tests.

## Current palette: lighter gray panels

The overall background, Dark diagrams, and white-key fill move from `#323232` to `#585858`, reusing the existing Bitwig-style toolbar's lighter neutral.
Black keys remain pure black. Lines move to `#B2B8C0` and octave/secondary labels to `#D1D5DA` to retain contrast on the lighter surface.
Note colors, fixed white labels, exterior rims, and halos are unchanged. The JUCE surround now uses the generated `theme.toml` background, avoiding stale dark edges.
This section supersedes historical background colors below; Bright diagram surfaces retain their previous light fill.

561 pytest cases, 6 CTest groups, and the real CLAP probe pass. Bitwig 6.1.4 was reloaded and checked for panel/key/border colors and note press/release;
release restores a pixel-identical idle image. Library was saved/backed up, the shared CLAP installed, and focus restored.
MIDI, volume, and chord logic are unchanged. Hardware inputs, all timbres, and the REAPER host were not retested. Evidence: `target/chordlab-light-panel/`.

## Current visuals: fixed white labels and exterior halos

This section supersedes historical black active labels, inset rings, and strong brightness jumps below.

- All note labels stay white, with identical font size and core marker radius before/after activation.
- Idle fills are softer, less saturated, and slightly lighter; active fills are deeper/more saturated within the same hue family, without a large luminance jump.
- Active in-key notes get a 0.8 px exterior white rim plus two soft, same-hue halo layers, without reducing text space.
  The halo extends up to 3.3 px beyond the unchanged core radius. Out-of-key physical MIDI remains gray with a gray halo and no in-key white rim.
- Piano, guitar, and staff share the renderer; both Bright and Dark use white labels. Fractional-center circles apply alpha only once.
- MIDI, audio, volume, H/L recall, and S/A header are unchanged. Candidate/current anchor dots remain Guitar-only.

Changes: `lib/tools/chordlab/theme.toml`, `generate_theme.py`, generated `theme.jsfx-inc`,
`ui.jsfx-inc`, and `tests/test_theme.py`.
553 pytest cases, 6 CTest groups, and the real CLAP probe pass. Bitwig 6.1.4 checks cover an E chord, held H/L, and release.
Returned-anchor and released note diagrams match pixel-for-pixel; sampled white glyph pixels are identical idle/active, and the halo is outside the original dot.
The shared CLAP is installed, Library reopened, and focus restored; the project is byte-identical to its pre-test saved backup.
Physical MIDI/guitar, all timbres, and the REAPER host were not retested this round. Evidence: `target/chordlab-note-halo/`.

## Current interaction: no fingering preview highlights

There is no separate preselection/audition step or brighter idle hand-region fill.
Background scale/chord notes retain their normal dim colors; only active notes brighten and receive in-key rings. Physical MIDI highlighting is unchanged.
The hollow/filled anchor dots indicate available/current H/L positions, not an extra fingering-selection control.

- Press a chord key to sound its remembered position. A fresh Guitar instance resolves to the available anchor nearest fret 11.
- H/L moves one lower/higher Piano inversion step (not a whole-chord semitone shift), or one lower/higher available Guitar index anchor.
- Hold the chord while moving for immediate MIDI/display updates; release removes active highlights. Idle navigation changes memory without auditioning.
- Each degree remembers its position without a confirmation/save shortcut; Piano and Guitar memories remain independent.
  Persistence across restarts still requires saving the DAW project with plugin state. In-plugin recall does not automatically write the Bitwig project file.
- Guitar still plays every distinct pitch in its three-fret chord region for user refinement. Seamless 25×25 px S/A squares are unchanged.


Verification: 532 pytest cases, 6 CTest groups, and the real CLAP probe pass, including new automatic-recall checks across both modes and all seven degrees.
Bitwig held H/L, release/repress, and exact return pass. Idle note diagrams are pixel-identical across anchors, with no preview fill.
Library is saved with focus restored. Evidence and backups: `target/chordlab-no-preview/`.


## 0.2.4 seamless header

Both key-strip-to-S and S-to-A gaps are zero. The key strip expands to fill the reclaimed space; height, colors, and behavior are unchanged.
542 pytest cases, 6 CTest groups, and the CLAP probe pass. After reloading Bitwig, pixel checks confirm both seams are continuous across all 25 rows.
Independent S/A clicks pass; S is off and A on. Saved Library/plugin backups, logs, and screenshots: `target/chordlab-seamless-header/`.


## 0.2.4 current behavior: full-region MIDI and active-note rings

This section supersedes the representative grip, four-fret region, display-only candidates, and static grip rings below. Earlier entries are retained as history.

- **K = Guitar**: the anchor plus the next two frets, three frets total (e.g. 6–8).
  Collect every current-chord tone on all six standard-tuned strings in that region; deduplicate exact MIDI pitches and play all of them simultaneously. Octave-separated notes remain distinct.
  No three-finger, one-note-per-string, contiguous-string, or six-voice restriction. This is a study pitch set, **not a guaranteed physically playable simultaneous grip**.
- **H/L** move through lower/higher anchors while a chord is held, releasing the old set before sending the new one; boundaries do not retrigger.
  **J = Piano** preserves the previous close voicing, independent position memory, and inversions. Tab still cycles triads/sevenths/ninths.
- Sevenths keep the user's four transposed anchor families. Triads/ninths start with anchors 1–14.
  All types remove one-fret neighbors, preferring more chord-tone string/fret locations, then the lower fret on ties; retained anchors are at least two frets apart.
  In C major, Bm7b5 now retains **3, 6, 10, 12, 14**. This is coverage ranking, not verified ergonomics.
  Default remains nearest fret 11; obsolete saved anchors resolve to the nearest candidate, lower on ties.
- Piano, guitar, and staff share highlighting: faint background tones, brighter idle region candidates, and bright **white-ringed** active in-key notes.
  Rings represent computer-chord or physical-MIDI note ownership, not a static chosen grip. Out-of-key physical MIDI stays gray.
  Matching **absolute pitches** light together across diagrams, not every octave of a pitch class.
- Rings stay inside the existing marker diameter, bounded by black-key width. Hollow/filled anchor markers and soft S/A colors remain.
- No timed strum: all notes are emitted at the same event offset. Larger simultaneous sets may sound louder; audition at a lower instrument/track level.
- The 21 CLAP parameters, v3 state, and stable ID remain unchanged. `Voice 1..6` remain compatibility diagnostics for the first six notes, not a total-voice limit.
  Internal capacity is 18; the current full catalog reaches 9 distinct pitches. Physical MIDI is not revoiced.

Implementation: `guitar.toml`, `generate_guitar.py`, and `guitar_table.jsfx-inc` define pitch-union records;
`guitar.jsfx-inc` handles lookup/navigation; `midi.jsfx-inc` sends the actual record length and releases every voice slot;
`ui.jsfx-inc`, `theme.toml`, and `generate_theme.py` implement shared highlighting and active rings.
The same installed CLAP is shared by Bitwig/REAPER and requires a host reload. No separate JSFX product is maintained.


### 0.2.4 verification

541 pytest cases, 6 CTest groups, and the real CLAP probe pass; 119 Rust tests and strict Clippy also pass. The catalog covers 12 keys × 7 degrees × 3 types,
1,520 regions total. Independent six-string/three-fret enumeration checks actual MIDI pitch unions, complete chords,
deduplication, navigation, and release. Additional coverage verifies mixed-input ownership beyond six voices,
sustain/focus-loss cleanup, open-anchor persistence, and legacy state import.
Bitwig 6.1.4 checks held 0→3→0 navigation, J switching, and release. Screen checks cover 864 fretboard positions
and both piano ring maps; the returned-position image is pixel-identical. Library was saved before testing and
reopened afterward, with its file byte-identical to the backup, A green and S off.
Evidence, old plugin, and project backup: `target/chordlab-region-midi/`.
No fresh physical MIDI/pedal/guitar, all-instrument level, or REAPER-host tests were performed; injected MIDI covers mixed ownership.

## 0.2.3 UI refinement and regression rerun

S/A retain 25 px squares and white letters, using muted red `#94646A` for off and muted green
`#567962` for on. Font size changes from 16 to 14 with regular weight and gentler hover brightening.
White-label contrast remains ≥4.5 in both normal and hover states. This same-version style update
does not change seventh anchors, MIDI, keyboard behavior or the state format.

Before changes: 531 Python cases, 6 CTests and the CLAP probe passed. After changes: 534 Python cases,
6 CTests, the real CLAP probe, 119 Rust tests and `cargo clippy --offline --all-targets -- -D warnings` passed.
Coverage includes 252 chords / 1725 shapes, held navigation, mixed input, state restoration and GUI lifecycle.
Reloaded Bitwig checks passed for S/A clicks, Space, focus transitions and rendered colors;
Library was saved and plugin focus restored. Physical MIDI/pedal/guitar input, all-preset listening and
a new REAPER host run are not included. Logs, screenshots, installed hash and backups:
`target/chordlab-soft-controls/`.

## 0.2.3: user-defined seventh-chord anchors

Guitar sevenths use the user's Cmaj7 / Dm7 / G7 / Bm7b5 index-anchor families, transposed by
root and repeated every 12 frets. H/L and the upper marker row share that catalog; triads/ninths are unchanged.
Open anchor 0 survives state restoration. Retired saved anchors resolve to the nearest available position,
with lower-position tie breaking. Half-diminished anchors provisionally retain 2, 3, 6, 7, 9, 10, 12;
6/7 remain distinct and human play-testing is still required.
[Position table and scope](GUITAR_VOICING.md#user-defined-seventh-anchors-023).
531 pytest cases, 6 CTests, the CLAP probe and Bitwig marker/held-HL/transposition checks passed.
Evidence/backups: `target/chordlab-user-anchors/`. No new hardware or full-library acceptance run.

## 0.2.2: S / A square state buttons

The top-right controls are 25 × 25 px squares, matching the adjacent key-selection button height:
**S = Sustain**, **A = Active**. White letters, dark red off, dark green on; A is green only
when computer-keyboard input is enabled and the plugin has focus. Clicking, Space for Sustain,
focus synchronization, and hardware MIDI behavior are unchanged.
428 pytest cases, 6 CTest groups, and the CLAP probe passed; Bitwig click, Space, and focus checks passed.
Evidence and pre-deployment backups: `target/chordlab-square-controls/`. This is not an all-preset or hardware retest.

## 0.2.2: all chord-tone candidates in the guitar hand region

The lower fretboard highlights all chord tones across six strings within four frets of the index
anchor, plus their exact-pitch duplicates across the neck. Candidate brightness sits between idle
and sounding notes. No extra MIDI output; clef mode selectors remain removed.
[Usage and scope](GUITAR_VOICING.md).

### 0.2.1 UI simplification

Removed both Piano/Guitar selectors beside the clefs, their click targets, hover labels and `Fret n` text.
J/K mode switching and the hollow/filled index-anchor row above the lower fretboard remain.
Notes and MIDI behavior are unchanged.

## 0.2.1: index-anchor markers

The lower Guitar diagram now shows hollow candidate anchors and one filled current anchor above
the strings, matching the existing fret-inlay dot size. H/L and key/degree/type changes update
the indicators. MIDI behavior and the fingering catalog are unchanged.
[Details and scope](GUITAR_VOICING.md#index-anchor-markers-021).

## 0.2.0: Piano / Guitar voicing

**H/L navigate, J selects Piano, K selects Guitar**, replacing G/V.
Preserves compact Piano voicings, adding complete standard-tuning guitar shapes
with index barre plus at most three fingers. Independent position memories,
filled/hollow mode selectors and physical-fingering outlines.
[Usage, implementation and verification boundaries](GUITAR_VOICING.md).

## 2026-10-18: final keyboard palette — gray white keys, black black keys

Following user clarification, Dark white keys match the background at `#323232`; both outer
and inner black-key fills are `#000000`. This supersedes the historical black-white-key scheme
below. Dividers, frame, highlights, Bright mode, and MIDI behavior are unchanged.
118 pytest cases, 4 CTest groups, and the CLAP probe passed.
Evidence and deployment backup: `target/chordlab-gray-white-black-keys/`.

## 2026-10-18: black white-key surfaces in Dark

Both piano diagrams now fill white keys with `#000000`, preserving the existing 2 px dividers
and outer frame. The independent `key_white` theme role leaves black keys, staff, fretboard,
note highlights, geometry, and Bright mode unchanged. This is a 0.1.10 asset revision shared
across hosts after plugin reload. Deployed and inspected in restarted Bitwig, including C-key
hold/release highlights. 118 pytest cases, 4 CTest groups, and the CLAP probe passed.
Evidence and previous binary backup: `target/chordlab-black-white-keys/`. This is not a new
full-library or physical-hardware acceptance run.

[Current cross-DAW status, installation paths and wrap-up](../bitwig_library/WRAPUP.md).
Historical entries are retained below. Current controls use Space Sustain, H/L navigation, J/K modes
and S/A square state buttons; Dark/Bright is saved per plugin instance.

[Legacy product retirement and revalidation](RETIREMENT.md)

0.1.6 uses an ordered X11 key/focus event stream with detectable auto-repeat.
This fixes repeat/release races around the system auto-repeat boundary; focus loss
releases held computer notes and cancels pending modifier taps.
Current results and binary hash: `retirement_acceptance.json`.

[0.1.5 left-hand controls and full regression](LEFT_HAND.md)

[0.1.4 focus regression](FOCUS_FIX.md)

0.1.4 fixes Keyboard focus indication: green only while enabled and focused, red otherwise.
Focus loss preserves the enabled preference; clicking back restores capture unless manually disabled.

0.1.3 removes the Panic entry and its tooltip; automatic note cleanup remains unchanged.

[0.1.2 control update acceptance](controls_acceptance.json)

**Current product: CLAP only.** The native JSFX/Lua/VKB workflow is retired.
The EEL files in `../chordlab/` remain the embedded engine source; changes require
rebuilding CLAP, not shipping two synchronized products. See [library migration](../library/CLAP_MIGRATION.md).

[0.1.1 font calibration and Core audition project](UI_CALIBRATION.md)

[中文](README.cn.md) · [Generic ysfx prototype history](PROTOTYPE.md)

[Mixed input, gray markers and Input FX workflow](MIXED_INPUT.md)

## One musical implementation, two hosts

The retired REAPER JSFX/Lua/VKB product is no longer maintained. The dedicated
`Chord Lab.clap` (`org.utrp.chordlab`) embeds ysfx plus six EEL/JSFX engine files,
notation image and image license. This is the same musical implementation, not a rewrite;
the engine UI now reserves room for the CLAP-owned controls. Its editor handles computer keys without
REAPER Lua or VKB. It is a MIDI effect, not a synthesizer or an audio-volume control.

## Use and manual acceptance

The production sound library already uses one shared CLAP Input FX. For another project,
save a backup and add the plugin before an instrument. Search FX for **Chord Lab (UTRP)**, rescanning
CLAP/restarting REAPER if necessary. Route:

`MIDI input → Chord Lab CLAP → Surge / piano instrument → audio effects`

Arm and monitor the track. Use MIDI channels 1–15; channel 16 is reserved for commands.
Hardware velocities pass unchanged; computer chords default to velocity 64. To record
the generated MIDI in REAPER, put CLAP in **Input FX**. Ordinary track FX recording does
not automatically record the generated notes. Disable the legacy Chord Lab Lua session
and global VKB capture during comparison, and monitor only one version at a time.
Do not put both versions in series.

The top-right squares are **S — Sustain** (left) and **A — Active** (right): muted green = on,
muted red = inactive, with white letters. Active is green only while keyboard input is enabled and focused; losing focus turns it red.
Clicking back restores green unless manually disabled, in which case click A to enable it.
Hardware MIDI is independent. The old toolbar
and shortcut sentence are removed. No Panic control or right-click menu is provided. Errors still
appear as a visible banner; normal instructions are tooltips only.

| Control | Expected behavior |
| --- | --- |
| Q W E R T Y U I O P [ ] | 12 keys; locked while sounding or playing, as in JSFX |
| Z X C A S D F | vi, viiø, I, ii, iii, IV, V (6, 7, 1, 2, 3, 4, 5); hold/release |
| H / L | Move Piano inversion / Guitar position lower or higher while holding chords; auto-save |
| J / K | Select Piano / Guitar mode directly |
| Tab | Cycle triad/seventh/ninth and remember immediately |
| Space / Sustain button | Toggle Sustain on press; no auto-repeat; pedal release cannot cancel the lock |
| Overlapping chord keys | Last held key wins; releasing returns to the previous held key |
| Switch away/back | Recall the degree's chord type and position |
| Save/close/reopen RPP | Restore memory; safely reset Sustain OFF |
| Lose focus | Release generated notes; click back to continue |
| Click green Keyboard | Clear held controls and Sustain, stop capturing; button re-enables |
| Close editor | Clear computer notes and Sustain; MIDI processor remains in the track |

Release keys before switching windows. After focus leaves, OS key repeat may trigger
the DAW's shortcut for the same key; this plugin does not intercept other windows.
Ctrl/Shift/Alt/Cmd combinations do not execute plugin commands.
Space works alongside held chord keys. Shift and Ctrl have no standalone actions.
Ctrl and right Shift are not standalone commands. Old Esc/Ctrl/H/J/K/L/semicolon/Enter actions are removed. Unmodified keys, including Space, are consumed
while enabled and focused **if the host delivers them**. Host-global/system shortcuts cannot be
unconditionally overridden by CLAP.

Check both staff/piano/fretboard groups and held-note highlights.
They display MIDI state, not instrument release/reverb tails. Focus loss sends note-offs,
not a mandatory sustain reset or audio mute; disable Keyboard when computer-input cleanup is needed.

## Evidence and limits

`left_hand_acceptance.json` and `target/chordlab-full-0.1.5/` record 0.1.5 results.
`acceptance.json` records the original port binary hash and audited results. Its historical local
artifacts are under `target/chordlab-clap-release/`. Historical `validation.json` refers
only to the old generic wrapper, not this dedicated product.

Coverage includes:
- Native JSFX vs CLAP ordered MIDI bytes and block-relative offsets: 12 keys, 7 degrees,
  all chord types/inversions, recall/reset, velocities 1–127 on channels 1/15, overlaps,
  Sustain/pedal, bend, CC, Channel/Poly Pressure and Program Change.
- Actual RPP save/close/reopen and settled host-parameter edits compared with native JSFX.
- Independent CLAP ABI host: ports, 18 parameters/defaults, X11 GUI support, 8 host writes,
  44.1/48/96 kHz × 32/64/256/1024 frames, short MIDI/Clock/SysEx, reset/reactivation,
  cross-instance state restore without temporary resource paths.
- Keyboard/queue unit checks for repeat, release/focus, overflow and failed-send cleanup.
- Real injected mouse/key events and screenshots in isolated headless Sway/XWayland.

This is **not a universal mathematical 100% equivalence certificate**. Still requiring
user/platform acceptance: physical MIDI/Spark GO audio, actual desktop shortcut settings,
long sessions, HiDPI/multiple monitors, Bitwig runtime, macOS/Windows, offline rendering,
abnormal unload/whole-chain bypass, recording routes and all transport combinations.
Native CLAP note expression, MIDI 2.0 and polyphonic modulation are not implemented.
Controller passthrough does not imply these features. REAPER multiple MIDI buses are
outside the current single-port model.

The old Lua sound library, track selection, paired Surge/VKB windows and recording
transport controls are not plugin features. Existing JSFX RPP chunks are not automatically
converted to CLAP state. Keep the original project; new CLAP memory saves in new projects.
Different DAWs' entire projects do not become interchangeable.

## Bitwig: static compatibility assessment only

The interface path is suitable, **not runtime certified**. Bitwig officially supports
CLAP alongside built-in devices. The intended chain is Chord Lab → Surge XT/another
cross-host instrument → effects. [Official plug-in guide](https://www.bitwig.com/userguide/latest/vst_plug-ins/)

This Linux x86_64 binary exposes one MIDI input/output, zero audio ports, stable parameters,
state and an X11 editor. It does not depend on REAPER APIs, Lua, interprocess gmem or an
external JSFX directory; resources belong to each instance. For first Bitwig tests,
Individually hosting can isolate failures. [Official hosting modes](https://www.bitwig.com/userguide/latest/vst_plug-in_handling_and_options/)

Next tests: scanning/category, MIDI channels/instrument output, keyboard focus/global
shortcuts, state reload, recording generated MIDI, transport/suspend and multiple instances.
Do not force MPE: channel 16 is reserved. macOS requires a separate build and acceptance.

## Implementation

`dependencies.toml` pins six archives with SHA-256. `prepare_build.py` verifies all inputs
before extraction and patches short MIDI/SysEx output. `port_upstream.py` applies checked
adaptations to the pinned ysfx host, not to the musical JSFX source:

1. Load the fixed script and 18 parameters during construction.
2. Consume pending host writes before slider readback, independently of delayed CLAP
   listener callbacks; snap stepped sliders like REAPER, including half-step boundaries.
3. Embed assets, use private temporary directories and path-independent state. Bounded
   SPSC keyboard events enter the audio thread; overflow requests cleanup.
4. Linux uses one ordered native X11 key/focus stream with detectable auto-repeat.
   Physical snapshots only initialize/resynchronize inactive capture; real key-up
   releases held keys, focus loss cancels pending modifier taps and releases notes.

The production build uses `CheckingLevel=Minimal`. This pinned helpers' Maximal flush
validator queries main-thread-only metadata during legal audio-thread flush, generating
false thread warnings; that debugging check is not enabled on the audio thread. Parameter
values still undergo finite/range validation.

## Build and reproduce

Requires Python 3.11+ with `tarfile` data-filter support, CMake 3.22+, C++17, Ninja and
JUCE Linux development libraries (X11, Freetype, ALSA, etc.). GCC/Linux is tested; this is
not a cross-platform build claim. Download the six configured URLs to
`target/chordlab-clap-build/downloads/<name>.tar.gz`; preparation is offline.

```sh
python lib/tools/chordlab_clap/prepare_build.py \
  --downloads target/chordlab-clap-build/downloads \
  --output target/chordlab-clap-build/deps
cmake -S lib/tools/chordlab_clap -B target/chordlab-clap-build/build -G Ninja \
  -DCHORDLAB_DEPS="$PWD/target/chordlab-clap-build/deps" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5
PYTHONPATH=lib/tools/chordlab_clap python -c "from pathlib import Path; from prepare_build import assets; assets(Path('lib/tools/chordlab'), Path('target/chordlab-clap-build/deps/chordlab.zip'), Path('lib/tools/chordlab_clap/prototype.toml'))"
cmake --build target/chordlab-clap-build/build -j 2
ctest --test-dir target/chordlab-clap-build/build --output-on-failure
python -m pytest lib/tools/chordlab_clap lib/tools/chordlab/tests -q
```

Preparation refuses an existing output; skip it when dependencies are already prepared.
Artifact: `target/chordlab-clap-build/build/ChordLab_artefacts/Release/CLAP/Chord Lab.clap`.
With a valid X11/XWayland DISPLAY:

```sh
target/chordlab-clap-build/build/clap_probe \
  "$PWD/target/chordlab-clap-build/build/ChordLab_artefacts/Release/CLAP/Chord Lab.clap"
python lib/tools/chordlab_clap/stage_port.py --plugin \
  'target/chordlab-clap-build/build/ChordLab_artefacts/Release/CLAP/Chord Lab.clap' \
  --output /tmp/chordlab-new-test
```

Launch REAPER with the generated isolated HOME, `-cfgfile .../reaper/reaper.ini` and
`prototype.rpp`. Run `ab_test.lua`, then `state_ab.lua`, then `parameter_ab.lua`; inspect
result files. The fixture uses Dummy Audio, 48 kHz/256 and no physical MIDI. Do not use a
personal launcher that modifies production settings. Scripts enforce scratch paths and
empty initial projects; staging refuses existing directories.

## Licensing / distribution

ysfx source carries Apache-2.0; JUCE 8 modules are AGPLv3/commercial dual-licensed;
CLAP/adapter use MIT; notation retains its own license. The old ysfx release ZIP's AGPL
license is not the library's license. This work is a local build, not a public release.
Preserve applicable notices and required corresponding source/build materials before
external distribution; do not represent a JUCE-linked binary as unconstrained by JUCE's
licensing. Dependency LICENSE files are retained in the build and local release archive.

## Square state buttons (2026-10-17)

Sustain / Keyboard now use flat 25 px-high rectangles like adjacent controls, without rounded corners or outlines.
Soft red Off / green On remain unchanged. Rendering only: click, focus, Sustain and MIDI behavior are untouched.
77 Python tests, 3 CTest groups and the real CLAP probe passed. Both buttons were toggled in Bitwig;
screenshot pixel checks confirm solid state-color corners in both states. The project was saved/reopened and editors restored side by side.
Evidence: `target/bitwig-flat-buttons/`.

CLAP SHA-256: `2b0379c201f6ca996d04f995c25777b61050c267fbb578ae6ba57cf9b9096b6e`.

## Dark / Bright appearance (0.1.7, 2026-10-17)

Right-click inside the diagrams and choose **Appearance → Dark / Bright**. Dark is the default.
The choice is saved per plugin instance with the project; it is not a global preference.
Dark uses Bitwig-matched `#323232` backgrounds, light-gray black-key shapes, muted key dividers,
light guitar strings, staff lines and notation. Inactive note markers are dimmed; active role colors remain unchanged.
Bright restores light diagrams. Sustain / Keyboard retain flat red/green state buttons.

Appearance is appended as parameter 19; existing parameter IDs 1–18 are unchanged.
Actual legacy Library state imports successfully and defaults to Dark. The menu releases computer-held
notes and suspends keyboard capture while open; ordinary theme parameter changes do not emit MIDI.

Validation: 97 Python tests, 3 CTest groups, actual CLAP lifecycle/state/GUI probe, 12 sample-rate/block-size
combinations, and mixed held-MIDI theme switching passed. In Bitwig, both palettes and notation were checked;
Bright survived saving and reopening the actual Library project. Dark was restored and saved; focus and
Sustain state indicators were checked. A fresh DAWproject export matched all 95 original sound-engine states
and contained no Chinese in project/metadata XML. This round does **not** constitute a new 98-sound audio
acceptance or Spark GO hardware test; those follow the user's visual approval.

Evidence: `target/chordlab-dark/`. Deployed CLAP SHA-256:
`bbc873f8efd93ae7b3c78d0788dd4ce900ff70d4947825c5cac855ec3db83a36`.

### Dark palette refinement (2026-10-17)

Dark black-key shapes now use neutral gray `#737373` / `#828282` rather than pale blue-gray.
Dark root/third/fifth/seventh/ninth markers use brighter red/green/orange/blue/purple; external
held notes use a lighter gray. Inactive markers blend 45% role color with 55% diagram background
(previously 35% / 65%). Active notes remain substantially brighter and use dark text for contrast.
Bright palette and all keyboard/MIDI behavior are unchanged. This is an asset revision of 0.1.7.

104 Python tests, 3 CTest groups and the CLAP legacy-state/mixed-MIDI probe passed.
Bitwig was saved, backed up, restarted and checked with a held/released computer-keyboard chord;
idle, held and released screenshots are in `target/chordlab-brighter/`. Final project is saved in Dark.
CLAP SHA-256: `143c91fcf39d6c42b7e1d474f8b857dd7a83e411d2147b105aec46fff2e598e6`.

### Subtle outer panel corners (2026-10-17)

Historical implementation, superseded by the 2026-10-18 straight-edge fix below.
The editor previously painted a small 8 logical-pixel rounded outer panel, using an opaque neutral
surround rather than relying on host-specific transparent windows. Only corner pixels are
masked after the EEL view; internal square buttons and diagram layout are unchanged.
Radius and surround color live in `../chordlab/theme.toml`; regenerate `editor_theme.h`
with `python lib/tools/chordlab/generate_theme.py` before building.
114 Python tests, 3 CTest groups, CLAP GUI resize/recreate, legacy-state and mixed-MIDI
probe passed. Bitwig was saved/backed up/restarted; all four corner pixels, antialiasing
and computer-keyboard input were checked. Evidence: `target/chordlab-rounded/`.
CLAP SHA-256: `ca46e3cf77d8592a9bc8867d19a73ece9566350f379a43875252605d335b675f`.

### Stronger Dark diagram separators (2026-10-17)

Dark piano white-key separators and an inward outer frame now use 2 px strokes. Dark guitar
fret separators also use 2 px, pixel-aligned; the 3 px nut stays unchanged. Their gray matches
staff lines (`#9098A1`). Bright mode, key geometry, marker centres/colors and MIDI are unchanged.
The width is configured by `dark_diagram_line_width` in theme.toml (integer 1–3).
122 Python tests, 3 CTest groups and the CLAP state/GUI/MIDI probe passed. Bitwig was saved,
backed up and restarted; held/released chord rendering and actual 2 px separators were checked.
Evidence: `target/chordlab-thicker-lines/`. CLAP SHA-256: `ec2192cc4e2389e97e2fe3439ba14fcc28bdf2851df71ab120a80b78630e0625`.

### Clean edges and relative-minor labels (2026-10-18)

Removed the opaque 8 px corner overlay and generated `editor_theme.h`: it exposed dark
rectangular corners inside the host-owned opaque X11 window. Clean square edges replace that
historical implementation. Dark diagram stroke weights, note sizes and Bright mode are retained.
The first row now uses minor-first pairs (`Am/C`, `Bbm/Db`, ...), fitted within existing buttons.
This is relative-key naming only; chord degrees, note colors, voicings and parameter IDs stay stable.

Key commands now call `slider_automate(1)` as well as `sliderchange(1)`, so hosts receive changes.
The pinned CLAP adapter also needs global parameter events to set note_id/port/channel/key to -1,
not zero. `prepare_build.patch_global_parameters` applies this validated patch on clean builds.
The new probe checks the actual outbound Key event and rejects the old note-0 targeting.
For Bitwig project Root Key/Scale integration, see `../bitwig_library/README.md`.
The same UI-originated parameter/gesture events are marked `CLAP_EVENT_IS_LIVE`;
the probe checks this flag as well as the wildcard target fields.

## 0.1.8: held-chord navigation and click focus

Hold C (or Z/X/A/S/D/F), tap G to move up-right or V to move down-left.
The chord keeps sounding; each real press moves once and OS repeat is ignored.
Esc and Ctrl no longer move voicing. Standalone left Shift release still toggles
Sustain; Space and Tab are unchanged.

With user approval this machine now uses Sway `focus_follows_mouse no`: hovering
another window does not change focus; clicks and focus shortcuts still do.
This is a desktop-wide policy, not plugin focus stealing. Genuine focus loss still
turns Keyboard red and safely releases computer notes.
See [G/V and focus acceptance](GV_FOCUS.md).

## 0.1.9: Space toggles Sustain

Each real Space press toggles Sustain, including alongside held chord keys. Holding and releasing
Space do not toggle again. Standalone Shift and the former Space reset shortcut are removed.
G/V, Tab, the Sustain button, click-focus policy and hardware MIDI routing are unchanged.
The 0.1.8 and earlier acceptance sections above describe historical versions only.

0.1.9 acceptance: 118 Python tests, 4 CTests, 199 keyboard checks and 1012 pairwise sequences passed.
New real-CLAP checks cover press-only Sustain toggling, repeat/release suppression and no chord reset;
G/V, legacy state, mixed MIDI and GUI lifecycle checks passed. In Bitwig, Shift did nothing,
Space press/hold/release stayed On, the next press turned Off, and Shift+Space did not trigger.
Library was saved and reloaded. Evidence: `target/chordlab-space-sustain/`; installed SHA256:
`3ceeeb44218c56ad1ad67a5a8506c80e130c10fd782a48f760450350848e8971`.

## 0.1.10: status dots and brighter notes

Top-right: Sustain on the left, Keyboard on the right. Each 14 px red/green dot has a 25 px click target.
Names remain in tooltips/accessibility. Both share the tonality row centerline; twelve tonality buttons
expand across the remaining width. Click actions, Space, G/V and focus behavior are unchanged.
Dark idle-note color mix increases from 45% to 55%; active colors are slightly brighter too, retaining separation.

### Deploying changes to DAWs

`theme.toml` configures the palette and dot layout. CMake generates the EEL theme and C++ controls,
then repackages current engine assets into CLAP; no separate manual asset refresh is needed.
Bitwig and REAPER share `~/.clap/Chord Lab.clap` on this machine. Source edits are not live updates:
build, deploy, save the project, then reload the plugin (safe DAW restart here).
The stable CLAP ID lets existing projects load new binary assets while restoring parameters/chord memory,
without replacing every track. Other machines need a compatible platform binary copied separately;
this is not cloud synchronization, and Bitwig/REAPER project files remain independent.

0.1.10 acceptance: 127 Python tests, 4 CTests and real-CLAP state/GUI/mixed-MIDI/key probes passed.
Deployed, saved and restarted Bitwig Library; verified both dot clicks, tooltip and held-chord G/V,
and visually checked note brightness. Library controller synchronization was verified with
Bbm/Db → B♭ Minor and G#m/B → G# Minor, then restored Am/C → A Minor,
Sustain Off and Keyboard On, and saved. This synchronization requires the Library controller
and Project Remotes; it is not generic CLAP host-key control and does not transpose recorded clips.
This round did not retest every sound or the physical MIDI keyboard.
REAPER synth.rpp and Guitar Frontend binary hashes remain unchanged.
Evidence: `target/chordlab-dot-ui/`; installed SHA256:
`ea232a33fe70c9e3bf5719cf899ac90f5c0eb59fb9132cfee28c0a43e28ed044`.

## 2026-10-23: Library cold-start Focus / Active repair

- Library controller 0.11 opens the shared Chord Lab once even when the saved selection is a folder or empty. Device readiness has bounded retries. This branch preserves sound activation, Arm, Monitor and other editors; ordinary projects remain excluded.
- Chord Lab 0.3.6 defers initial keyboard focus until the host opening transaction settles and transfers focus from its own active host container into the keyboard peer. Manual A OFF and focus outside this editor are respected. `theme.toml` exposes `interaction.focus_settle_ms=300` separately from visual colors.
- The existing `utrp-plugin-windows` policy activates only a newly discovered Library shared editor, once, while focus is still within that same Library main window/editor. Game resizing, dragging, leaving the application and normal polling do not reclaim focus. No new service was added.
- Validation: 927 Python tests, 12 CTests and isolated Sway CLAP input/state/focus probes passed. The new late-host-container-focus assertion fails on 0.3.5 and passes on the final build. Real Library cold start produced green S/A without clicking the plugin/A; computer A triggered notes and the Bitwig meter. Leaving focus on the main window for 3 seconds did not reclaim it; returning restored A.
- Evidence: `target/focus-startup-20261023/`. Use compositor-managed probe windows: early override-redirect probes returned PointerRoot under rootless Xwayland and are not production-regression evidence. Final comparison: `probe-old-host-settle.log` / `probe-final.log`.
- Physical MIDI/guitar listening and every preset were not retested this round. Plugin SHA256: `9f35503a54f4414ee11aa16c6675c4192e2c6d4cc3375be64a57c0ad6c2b9a41`. Original backups: `~/storage/daw/Backups/chordlab-focus-20261023/`. No automatic commit/push.

## Game-panel spacing and corners (2026-10-23, 0.3.7)

- Game UI only: `#494949` matches both left capsule strips. Top/bottom/right outer margins are 20 px; countdown top aligns with the key strip. One rounded clip covers the panel and countdown, using the strip radius `choice_height / 2` (14.5 px). Normal dimensions, embedded theme, audio and scoring rules are unchanged.
- Score cards: 20 px top spacing, 52 px height, 20 px below. Key/modulation explanations have 12 px clearance before chords. Spacing lives in `chordlab/theme.toml` under `game_layout`; long previews remain scrollable above settings.
- Green `+N` beside the winning total lasts throughout Demo (including pause), then clears on the next question. Timeout and the losing side show no award. Isolated CLAP MIDI simulation observed piano `+79`, guitar `+96`, and retained totals without stale awards on the next question. This is not physical-instrument audio acceptance.
- Validation: 932 Python tests, 12 CTests, three-height render/pixel/transparent-corner/spacing/wheel checks; root and `chordlab_game` cargo tests and clippy with `--all-targets -- -D warnings` passed. Evidence: `target/game-spacing-20261023/`.

- Follow-up in the same update: preview whitespace adapts to available height without shrinking fonts/capsules. The default window fits **9 chords + 3 key badges + 3 modulation explanations** above settings. Shorter custom windows retain clipping/scrolling without overlapping settings; drawing and scroll limits share the same height calculation.
- Every approach and modulation bridge/pivot (`kind=1/2`) uses a gray capsule plus destination-relative degree dot, even when fully diatonic. Completed transitions stay hollow/black. Real arrivals/targets keep their palette. Fixed missing transition flags in the F-major screenshot fixture; added Rust bridge/pivot relative-palette regression tests.

- Final deployment: Library saved and reloaded on Workspace 2 with 0.3.7 (SHA-256 `1efee0fae0328be388a538bb21b993c60a6138f767259e0844dbf12125b3f321`). Normal startup showed green S/A; expanded live UI confirmed gray rounded panel and alignment. Game is paused (Resume button); no DAW recording was started. Screenshot: `target/game-spacing-20261023/live-final.png`. Physical-instrument audio was not re-accepted in this UI task.

## Fixed-major notation and actual major/minor harmony (2026-10-23, 0.3.8)

- Notation is independent from harmony. Relative major/minor pairs share major-based degrees and colors. Left slots remain `vi, vii, I, ii, iii, IV, V` (blue, blue, red, green, green, gold, gold); minor scale arrays no longer re-index these slots. Ordinary right-side target capsules use the same degrees while the key badge explicitly retains `major/minor`. Approaches and modulation bridges retain neutral capsules and destination-relative degrees/dots.
- Left selection requires matching root pitch, spelling and complete quality. External chords neither replace a diatonic capsule nor select an unrelated same-letter slot. Correct-note visibility, scoring and Demo remain independent.
- The numeric cycle still constructs chords in the actual mode: A minor `1→3→1` generates `Am7→Cmaj7→Am7`, displayed as `vi→I→vi`, not a C-major exercise. `Target.degree`, coverage and `(tonic, minor)` training identity remain mode-relative.
- The existing engine already supports 12 major and 12 minor keys. No RNG probabilities, voicing or scoring algorithms changed. Each of `dominant/shared_chord/diminished` was simulated for 4,800 sevenths: both cross-mode directions and same-mode transitions occurred, always after successful seven-degree coverage. Routes remain conditional on musical reachability, not universally available for every key pair.
- Validation: 1,310 related pytest cases, 12 CTests, root/game `cargo test` and `cargo clippy --all-targets -- -D warnings`; actual JSFX pixel checks for 24 keys × 7 targets × 3 widths including external rejection. The isolated CLAP showed F# minor with blue `vi F#m7` on both sides. Injected MIDI earned 69 points, displayed `+69` throughout Demo and cleared it on the next exercise. Normal controls and voicing memories remain unchanged.
- Evidence: `target/game-fixed-left-20261023/`; permanent regressions in `tests/mode_practice.rs`, `chordlab_game/presentation_tests.rs` and `chord_choices_probe.jsfx`. `minor-tonic.png` is a real CLAP screenshot from the silent isolated host, not live Bitwig.
- Installed through the Storage-backed `.clap` entry, SHA-256 `08ec9f61167afb66433379f6acaf649ea8337c0171bd654fe44e2d0dde236255`. Old 0.3.7 and on-disk project backed up under `~/storage/daw/Backups/chordlab-fixed-major-20261023/`. Save/reload was approved, but no Bitwig process or real Sway session was running: no save/reload is claimed, the Library file was untouched, and next launch loads the update. All 10 Storage links passed. No physical audio acceptance or recording occurred.

## Capsule game settings (2026-10-23, 0.3.9)

- `Play 10 s / Demo 2 s / Mod 50 %` share one row. Start/Restart, Pause/Resume, numeric fields, register ComboBox, Approach toggle and popup items all use capsules. Height derives from chord capsules (`29−2×3=23 px`), radius is half-height, and fonts follow the actual fitted left-hand size. Widths accommodate two/three controls per row or a full-width field.
- Settings height is derived as 134 px, anchored at the bottom with more central whitespace. Dense previews gain space; measurement, painting and scrolling share the same settings height.
- LookAndFeel belongs only to GamePanel, never the application or normal mode. Leaving game mode also hides its dropdown. Wheel steps/ranges/reversal, restart-time settings, scoring and harmony behavior are unchanged.
- Game capsules and settings share a real platform sans face. DejaVu Sans is absent on this system; requesting its point-height produced a null Typeface in JUCE's default button layout. Isolation tests caught the crash; selecting the platform face avoids it.
- Added 3 widths × 3 heights checks: equal control heights, no overlaps or clipping, one numeric row, uncompressed maximum `120 s/10 s/100 %` strings, transparent corners, matching fonts, wheel bounds, and dropdown/toggle states. Evidence: `target/game-capsule-controls-20261023/`.

- Final fixes: the countdown remainder uses the panel background directly, without a contrasting track. The rounded, transparent menu is embedded inside GamePanel rather than relying on a transparent X11 top-level window. Live preview confirms no white menu corners or overflow.
- Final validation: 1,360 relevant pytest cases, 12 Chord Lab CTests, 2 Guitar Frontend CTests, installed CLAP ABI/state/sustain/input probes, and root/game Rust tests and Clippy pass. A 180-round production-engine simulation includes 56 approaches, 7 modulations and 16 timeouts; independent scoring and byte-for-byte normal-mode MIDI against HEAD pass. Isolated live-window MIDI arpeggios produce Piano +26 and Guitar +74; only cumulative totals remain after Demo.
- Installed 0.3.9 SHA-256: `0ca1b9a9f91cff90307f49c987f5aa04d9aeac365a1c48c1c8054d6fb3e4973a`. Previous 0.3.8 and on-disk Library are backed up in `~/storage/daw/Backups/chordlab-capsule-controls-20261023/`. Real Bitwig opened Library on Workspace 2; Keystation USB is detected, but Spark GO is absent from USB/ALSA/PipeWire and Bitwig reports `No Output Device Present`, leaving its audio engine inactive. **Physical keyboard/guitar/speaker and running-host acceptance remain pending USB audio reconnection; isolated tests are not a substitute.** No recording, audio configuration changes or new scenes; no project save or commit/push this round.

## 2026-10-23: Bitwig hidden focus proxy fix (0.3.10 candidate)

- Observed cause: Sway already focused the shared Chord Lab container, but X11 focus remained on a sibling child of the host wrapper: an offscreen `1×1 InputOnly` proxy at `(-1,-1)`. The old `hostHasFocus()` recognized ancestors only, so a late host handoff left A red. This is separate from MIDI/Sustain parameters or audio routing.
- Extend native focus handoff only to a viewable `1×1 InputOnly` sibling with the exact same immediate parent as the peer. Visible InputOutput controls, another editor's proxy and other applications do not match. Existing `enabled` gating still respects manual A-off. No periodic global focus grabbing, startup delay increase, controller or layout-service changes.
- The actual CLAP regression reproduces failure on installed 0.3.9. Candidate 0.3.10 passes six editor recreations and eighteen delayed proxy handoffs, plus delayed mapping, ancestor focus, sibling-control isolation and other-window/proxy isolation. 1,360 relevant pytest cases, 12 CTests and game rendering regressions pass. Evidence: `target/focus-stability-20261023/`. Real Bitwig deployment/restart acceptance awaits permission for a brief interruption; this entry does not claim deployment.
- Additional validation: root and `chordlab_game` pass `cargo test --offline` and `cargo clippy --offline --all-targets -- -D warnings`. Source and candidate build remain local, without commit/push; the live installed version is still 0.3.9.

- Subsequent deployment: on the repeated report, Bitwig was fully stopped and the live plugin was still 0.3.9. Backed up to `~/storage/daw/Backups/chordlab-focus-proxy-20261023T164424/`, then installed 0.3.10 through the existing Storage symlink, SHA-256 `e61cfd27cdb3cb501bb35e60eefa51b665584bd51a8be0ab9daa0967f6406a0c`. First real cold launch reached green S/A without clicking the plugin or A, with X11 focus on keyboard peer `0x1a00004`. A direct computer A key produced note highlighting, five sfizz voices and Master activity. The main window retained focus after switching to it. Test chord changes were not saved into the original Library; no recording was enabled and Spark audio routes remained connected.
- Real-host acceptance: three complete Library cold launches reached green S/A and keyboard-peer X11 focus after only Trial Continue, without clicking the plugin or A. Workspace 1 retained other-app focus; returning to Workspace 2 handed focus back. Manual A-off stayed red across focus changes, while a fresh cold launch still defaulted to enabled. The third freshly opened normal-mode session remains available for user listening confirmation. The on-disk Library hash equals the pre-deployment backup; no test chord changes or recordings were saved. Backup tests: 26 passed; all 10 live Storage checks passed. No commit/push.
