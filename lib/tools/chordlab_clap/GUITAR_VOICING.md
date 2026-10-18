# Piano / Guitar voicing — 0.2.4

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


[中文](GUITAR_VOICING.cn.md) · [Product](README.md)

Verification: 532 pytest cases, 6 CTest groups, and the real CLAP probe pass, including new automatic-recall checks across both modes and all seven degrees.
Bitwig held H/L, release/repress, and exact return pass. Idle note diagrams are pixel-identical across anchors, with no preview fill.
Library is saved with focus restored. Evidence and backups: `target/chordlab-no-preview/`.


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

## Controls

### User-defined seventh anchors (0.2.3)

These are the user's practice positions, not score-verified standard CAGED fingerings.
Only Guitar seventh-chord catalogs change; Piano, triads and ninths retain their behavior.

| C major reference | Reference anchors | Diatonic family |
|---|---|---|
| Cmaj7 | 0, 3, 5, 8, 10, 12 | I, IV |
| Dm7 | 2, 5, 7, 10, 12, 14 | ii, iii, vi |
| G7 | 0, 3, 5, 7, 10, 12 | V |
| Bm7b5 | 2, 3, 6, 7, 9, 10, 12 (provisional) | viiø |

Transpose by the target root's semitone distance from the reference, repeat every 12 frets,
and retain fretted positions 1–14. Bm7b5 therefore also has anchor 14, repeating anchor 2.
6/7 and 2/3 remain separate positions, not a fictional single barre. The earlier independent
mention of 9 is retained; the later repeated 9 was corrected to 6. This recollection needs play-testing.
Anchor 0 is enabled only for the explicitly requested Cmaj7/G7 open positions, not automatically
added to Dm7/Bm7b5 by modulo arithmetic. Open strings are not an index barre; transposed fretted
positions remain movable closed shapes.

The existing rules still choose one complete four-note representative per position. Matching an
index anchor does not reconstruct the user's exact string/finger choices. All chord-tone candidates
in the four-fret region and their exact-pitch duplicates remain visible, without extra MIDI output.
Markers, H/L, representative fingerings and MIDI share one catalog. Retired saved anchors resolve
to the nearest position with lower-anchor tie breaking; open anchor 0 survives save/reload.

Verification: 531 pytest cases, 6 CTests and the real CLAP probe. All 12 keys × 7 seventh degrees
have independently checked anchor/shape transposition; all 252 combinations / 1725 shapes pass
pitch, navigation and region-display regression. Bitwig checks cover four references, IV/iii/vi,
Dbmaj7 and held 0→3→0 navigation. The pre-test Library settings were restored.
Logs, screenshots and backups: `target/chordlab-user-anchors/`.

The top-right S (Sustain) and A (Active) squares use 14 px regular white letters, muted red for off and muted green for on.
Click S or press Space to toggle Sustain. A indicates enabled computer-keyboard input with plugin focus;
hardware MIDI does not depend on A.

With plugin focus and A green:

| Key | Action |
|---|---|
| J | Select Piano, retaining compact voicings |
| K | Select Guitar, generating MIDI from standard-tuning fretted shapes |
| H / L | Piano: lower/higher inversion; Guitar: lower/higher fretboard position |
| Z X C A S D F | Degrees 6, 7, 1, 2, 3, 4, 5 |
| Tab | Triad / seventh / ninth, automatically remembered |
| Space | Sustain on/off |

Hold a chord key while using H/L/J/K. G/V are retired.
The clefs no longer have Piano/Guitar selectors, hover labels, `Fret n` text or invisible click targets.
Use J/K to switch modes; note distribution and the index-anchor row below provide visual context.

Extra pale rings on the lower guitar diagram mark the selected physical fingering.
Other lit dots show the same absolute MIDI pitch on other strings, not additional fingers to press.
Octave equivalents are not the same absolute pitch. Piano and staff reflect actual sounding notes.
Hardware MIDI passes through unchanged. Guitar mode changes voicing, not the downstream instrument sound.

### All chord-tone candidates in the hand region (0.2.2)

In Guitar mode, the lower fretboard highlights every current-chord tone across **all six strings**
from the index anchor through anchor +3. A string can offer multiple alternative notes, independent
of the selected grip's sounding strings or remaining finger count. These are choices for sequential
playing, not a promise that all can be fretted simultaneously. The union of their **absolute MIDI
pitches** is highlighted at every matching location across the fretboard. Octave equivalents are
highlighted only if that exact pitch also occurs in the region, not just because the pitch class matches.

- Other chord tones keep the original dim fill.
- Region candidates and exact-pitch duplicates are brighter, including when no key is held.
- Sounding notes remain brightest; pale rings still identify only the selected grip.

The upper scale diagram, piano and staff do not receive candidate highlights; sounding-note behavior
is unchanged. MIDI output, grip/anchor selection and state format remain unchanged, with no additional
notes emitted. Span comes from `guitar.toml` (`fret_span`), brightness from `theme.toml`
(`guitar_candidate_mix`). For Emaj7 at fret 12, E4 at D-string fret 14 is now a candidate even though
the selected six-string grip omits it. Its exact-pitch duplicates light too, but not E2 merely by name.

0.2.2 verification: 426 pytest cases, six CTests and the real CLAP probe passed. EEL independently
enumerates the six-string/four-fret region for every anchor of all 252 key/degree/type combinations
and compares membership for all 128 MIDI pitches. Bitwig checks covered sustained H/L, J/K, Tab,
key changes and release. Screenshot pixel checks confirm matching candidate fills for E4 duplicates,
dim E2, brighter sounding E3, and restoration on release. Library was saved and left ready to play.
Build/test logs, screenshots and previous plugin/project backups: `target/chordlab-region-notes/`.

### Index-anchor markers (0.2.1)

In Guitar mode, a row **above the lower chord fretboard** shows available index anchors for the current
chord: hollow circles are alternatives; the filled circle is the selected anchor. Their radius matches
the existing single/double fret inlays below, with centres aligned to the corresponding fret cells.
H/L, key/degree/type changes and state restoration use the same catalog resolution as the actual MIDI
voicing, with no separate UI selection state. Piano mode and the upper scale diagram omit this row;
the fixed lower inlays remain unchanged. These are position indicators, not additional notes or MIDI
commands, and do not imply that every string at that fret must be barred.

This update adds visualization only. The conservative catalog below has not yet been replaced by
curated fingering families or human-tested grips. Notes requiring sequential finger movement are
not added to a simultaneously sounding chord.

0.2.1 verification: 413 pytest cases, six CTests and the real CLAP probe passed. EEL checks
every candidate of all 252 key/degree/type combinations for exactly one filled marker, matching
candidate counts, H/L updates and nearest-anchor resolution. Bitwig checks covered held H/L,
J/K, key changes, Tab and degree changes. Emaj7 at fret 12 was restored and saved.
Screenshots, build/test logs and previous plugin/project backups: `target/chordlab-anchor-markers/`.

## Conservative first version

- E2 A2 D3 G3 B3 E4 standard tuning; visible frets 0–17.
- Fretted index anchor 1–14, single note or barre, at most three other fingers, one string per finger.
  Version 0.2.3 additionally enables the explicitly requested Cmaj7/G7 open anchor 0.
- Anchor through anchor +3 (four frets), 3–6 contiguous sounding strings; only outer strings muted.
- Complete triad/seventh/ninth pitch-class sets, including fifth and ninth; repeated pitches/octaves allowed.
  Identical MIDI pitches are emitted only once even if present on two strings.
- One representative per usable anchor: prefer root bass, smaller stretch, fewer fingers, then more strings.
- Default nearest fret 11, not guaranteed frets 10–12. A few complete ninth chords require frets 5–7
  under these rules. No hidden omission is used to force a higher position.
- H/L clamp at catalog ends without wraparound or retriggering an unchanged shape.

This is a selected catalog, not a claim that barres are possible only at a few frets.
Apart from the explicit open anchor 0, open strings mixed with higher fretted positions are not included.
Thumb fretting, secondary barres, inner muted strings and personalized ergonomics are not included.
Passing geometric/finger-count constraints does not guarantee comfortable human fingering; play-testing is required.
Frets 10–12 and middle C are not equivalent register constraints; this version prioritizes the requested fret region.

## Implementation and persistence

- `../chordlab/guitar.toml`: tuning, span, preferred region and the four user-defined seventh-anchor families.
- `generate_guitar.py` emits `guitar_table.jsfx-inc` offline; no audio-thread combinatorial search.
- `guitar.jsfx-inc`: immutable catalog lookup/navigation; `midi.jsfx-inc`: six-slot ownership and mode changes.
- `ui.jsfx-inc`: index-anchor markers, fingering outlines and actual bass labels; previous palette retained.
- `keyboard-map.txt`: H/L/J/K.
- Existing 19 CLAP parameter indices retained, appending `Voicing mode` and `Voice 6`.
- State v3 adds seven guitar anchors, retaining v1/v2 loading. Piano and Guitar positions are independent;
  chord type remains shared per degree. Mode persists per instance.
- Single CLAP product, stable ID `org.utrp.chordlab`; same installation for Bitwig and REAPER.
  Reload the plugin in each host. Project-specific state does not automatically synchronize between hosts.

## Verification boundaries

- 413 Python tests across engine, wrapper, library and Bitwig helpers.
- Six CTests including pairwise keyboard sequences, all 252 chord combinations, fingering constraints,
  held-mode navigation, actual engine MIDI ownership and state restoration.
- Real CLAP host probe covers legacy state, 21 parameters, GUI lifecycle, sample rates/block sizes,
  H/L/J/K under held chords, state restoration and mixed MIDI.
- Local backups/logs: `target/chordlab-guitar-voicing/`, not versioned.
- This does not re-certify every preset, physical MIDI hardware, human fingering comfort or guitar pitch detection.

Bitwig 6.1.4 UI checks passed for held J/K and H/L, clickable mode dots, highlights and release.
An eight-second direct piano-track output capture measured approximately −5.72 dBFS peak, with no NaN/Inf. No microphone was recorded.

Reopening Library restored Guitar mode and fret 11. A fret-12 six-string Emaj7 example was then prepared and saved for audition.
Keyboard state tests additionally passed 217 checks and 1,200 pairwise press/release sequences.
