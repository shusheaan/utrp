# Full Bitwig Library migration — in progress

## Current: Keystation hardware controls

See [Keystation controls](KEYSTATION.md) for the separate Transport controller, transport/navigation buttons, CC7 slider, wheels and validation limits. Existing Generic musical input and Library controller remain; no Chord Lab sound-engine change.

## Latest: Ambient Guitar / controller 0.6

Four live guitar FX tracks were added under **Ambient Guitar**. Audio effects are independent of the shared, display-only guitar detection path. See [routing, controls, files, and validation](AMBIENT_GUITAR.md). This supersedes historical track counts below: the Library now has 113 tracks including groups and Master.

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

[中文](README.cn.md)

**Current status and complete storage map:** [2026-10-18 wrap-up](WRAPUP.md).
The history below includes superseded keys, appearance, routing and mode support;
use the wrap-up and controller 0.5 for current behavior. Hardware performance remains pending.

## Principles

Read `~/storage/daw/synth.rpp` without modifying it. Preserve saved plugin states, gains and groups.
The inventory contains 95 sounds: 93 Surge CLAP states and two sfizz pianos, covering all 88 repository FXPs.
Convert sfizz LV2 state to VST3 with its actual SFZ/Scala paths, CCs and synthesis parameters.
The Acoustic Piano uses the Retuned SFZ, not the outdated source marker.
DAWproject output is exclusive-create, never overwrite. Keep REAPER and shared CLAP binaries untouched until full acceptance.
The user approved replacing Basic Keys ReaVerbate with Bitwig Reverb; this is a different algorithm and must be disclosed.

## Tools

```sh
python lib/tools/bitwig_library/build.py ~/storage/daw/synth.rpp /tmp/Library-candidate.dawproject
python -m pytest -q lib/tools/bitwig_library/tests
node lib/tools/bitwig_library/tests/controller_test.cjs
```

`--probe` imports only four Basic Keys sounds. Shared MIDI input routing still needs host configuration.
The JSON inventory is not a host audio acceptance report.

`Library.control.js` and `Library.config.js` implement exclusive audition and editor opening using API 25.
They are scoped to `Library` / `Library-migration` projects with the shared input track marker.
Only one sound is activated; its instrument and the shared Chord Lab editors open on selection.
No MIDI regeneration or network listener. Installed in `~/Bitwig Studio/Controller Scripts/UTRP/`;
enable `UTRP Library` in Settings → Controllers. Bounded editor retries handle slow plugin loading;
new selections and project changes cancel stale requests.

## Validation and remaining work

- Eleven Python tests and the Node controller model tests pass, including slow editors and restored arm state; official DAWproject XSD validation passes.
- Four-sound probe: original sfizz samples load and produce audio; shared Chord Lab computer-keyboard routing to piano works.
- Saved project: `~/storage/daw/Library/Library.bwproject`, 108 tracks: 98 sounds, seven groups, shared MIDI, guitar and Master.
- All 95 original sounds and three retained pads pass shared-track MIDI → instrument audio and exclusive audition checks.
- All 95 original engines compared against actual Bitwig exports: Surge engine parameters, wavetables and tuning match.
- sfizz components initially matched byte-for-byte. After playing/reopening, Acoustic Piano additionally stores default `CC64=0`.
  The validator explicitly reports this byte difference and accepts only that pedal-off default, not arbitrary CC/engine changes.
- Saved, closed and reopened the final project. Piano, EP, compensated sound and all three pads pass reopened routing/arm/exclusivity checks.
- GUI recording of three computer-keyboard chords produced 12 exported MIDI notes. Test clips were removed; final export has zero test notes.
- Source RPP and both shared CLAP SHA-256 hashes are unchanged. Original three-pad backup:
  `~/storage/daw/Backups/bitwig-library-before-full-migration-20261017/`.
- Temporary Library Probe controller/script removed; TCP 19671 confirmed no longer listening.
- Spark GO is currently absent from the system device list; hardware end-to-end validation is not complete.

## Approved differences and operation

- Basic Keys group uses Bitwig Reverb: Room, Size 70%, Pre-delay 20 ms, Decay 1.60 s, Mix 12%.
  This is a light-reverb starting point, not a blind-listening-matched equivalent of ReaVerbate. Original instruments are retained.
  Select Basic Keys and adjust Reverb Mix (amount) / Decay (tail) in the bottom device panel; Ctrl-click enters exact values.
  Other groups retain their original Surge internal effects.
- Original `C2-distant` +12 dB exceeds Bitwig's linear-2.0 fader ceiling. A post-Surge Tool adds +5.9794 dB
  to the maximum fader, restoring the combined gain without changing Surge internal volume.
- Select a sound to activate it exclusively and open its editor plus shared Chord Lab. Click inside Chord Lab
  and confirm a green Keyboard button before computer-keyboard playing. Physical MIDI should not depend on editor focus.
  Reopened window geometry still needs visual review; the final piano and Chord Lab were manually placed side by side.
- Record to the selected sound track, not the shared input. Inactive tracks may retain historical arm flags;
  only the active sound participates, and the controller re-arms it after activation.
- Disable `Exclusive audition + editors` in Controllers before multi-track arrangement/playback.
  This controller is for single-sound Library research, not simultaneous multi-track production.
- Guitar chain: `Guitar Frontend → Chord Lab`, currently explicitly No input / Monitor Off.
  Restore raw Spark GO mono input when available, with detection before every guitar effect.
- Temporary HDMI audio remains disconnected from speakers for test safety; this is not an audible Spark GO setup.
  Pending: Spark GO recovery, actual monitoring output, physical MIDI/computer mixed performance, live guitar and hardware reopen tests.
  Do not delete REAPER before these pass.

Evidence: `target/bitwig-migration/`, especially `routing-audio.json`, `pad-routing-audio.json`,
`final-state-check.json`, `recording-notes.json`, `reopened-sample-routing.json` and `source-hashes.json`.

## Chord Lab appearance update (2026-10-17)

- Deployed Bitwig neutrals: background `#323232`, buttons `#494949`; retained light keys, staff/fretboards and note-role colors.
- Light panel labels pass 4.5:1 contrast checks across normal, hover, selected and disabled states. Sustain/Keyboard retain soft red/green.
- Rendering-only change: stable plugin ID, 18 parameters, keyboard controls, MIDI and state format.
  This appearance build retains version 0.1.6; identify it by SHA-256:
  `c9453048bbdf5925f94d809c588d28f50df4263ed024614c57fc588e0308450d`.
  Earlier unchanged-binary statements apply to migration validation. This update intentionally replaces shared
  `~/.clap/Chord Lab.clap`; REAPER will load the same new theme next time.
- This round: 88 Python tests, 3 CTest groups, controller model and real CLAP probe passed.
  Saved/reopened Bitwig, checked editor reopening on track selection, recorded computer-keyboard → shared MIDI → piano
  output (peak −9.32 dBFS), and visually checked Shift Sustain plus the red Keyboard state on focus loss.
- The full 98-sound matrix was not rerun for this rendering-only change; see previous migration evidence.
- Restart auto-connected temporary HDMI outputs. Testing temporarily disconnected speakers and restored those links afterward.
  This is not Spark GO monitoring validation: Spark GO remains absent, Guitar remains No input / Monitor Off,
  and real guitar plus physical MIDI mixed performance still need user participation.
- Backup: `~/storage/daw/Backups/chord-bitwig-theme-20261017-231405/`.
  Evidence: `target/bitwig-theme/` (screenshots, audio, tests and deployment hash).
  Original `synth.rpp` and Guitar Frontend are unchanged.

## Sources

- [Bitwig DAWproject](https://github.com/bitwig/dawproject)
- [sfizz VST3 state](https://github.com/sfztools/sfizz-ui/blob/develop/plugins/vst/SfizzVstState.cpp)
- [Steinberg streamer](https://github.com/steinbergmedia/vst3_base/blob/master/source/fstreamer.cpp)
- Controller API: local documentation bundled with Bitwig Studio 6.1.4.

## English-only Bitwig naming (2026-10-17)

All visible Bitwig names must use English without Chinese translations. Groups are now `Basic Keys` and
`Pad Lab - Ambient Research`. Use English for future tracks, groups, clips, scenes, device aliases and comments.
Chinese repository documentation is outside the Bitwig UI and may remain. The official Library was saved;
exported project.xml / metadata.xml contain no Chinese characters across 108 tracks, and all 95 migrated
sound-engine comparisons passed. Evidence: `target/bitwig-english/`.

2026-10-18 follow-up: the earlier XML export check missed the separate output tracks inside
the Basic Keys and Pad Lab groups. Renamed those through Bitwig to `Basic Keys` and
`Pad Lab - Ambient Research`, matching their outer groups, and saved Library. A read-only
scan of the saved native project found neither old Chinese label in UTF-8/UTF-16 and no
remaining printable Chinese candidates in length-prefixed UTF-16 strings. Embedded plugin
state entries are byte-identical to the pre-edit backup. This is not a full native-format parser.
Evidence: `target/english-ui-audit/`. Source REAPER projects and Chinese repository documentation
were not changed; future UI names must remain English-only.

## Minor-first project key link (2026-10-18)

`Library.key-sync.js` is loaded beside `Library.control.js`. In Library, the first two slots
of the saved Project Remotes `Perform` page are mapped to native `Root Key` and `Scale`.
An independent Project Remote cursor checks both mapping names and uses only the `Key` parameter from the shared Chord Lab's parameter updates. `Am/C` selects A Minor, `C#m/E` selects C# Minor, etc. Minor is looked up by
name, not an assumed scale-list index. Unavailable/remapped slots or unknown keys cause no writes.

The initial implementation was one-way; the bidirectional update below supersedes it.
This integration does not transpose recorded MIDI or analyze music. The existing major-degree chord engine, saved voicings and MIDI pitches are unchanged.
The existing Library-only controller setting must be enabled; other projects are untouched.
Keep the two Project Remote assignments. This host integration uses Bitwig 6.1 API 25, not a
portable CLAP project-key API; REAPER does not gain a global-key link from the plugin alone.

sfizz uses its installed native `Dark` theme, saved in
`~/.config/SFZTools/sfizz/settings.xml`; sample programs and tuning are unchanged.
Chord Lab's opaque rounded-corner overlay has been removed: its Bitwig-owned opaque X11 parent
cannot be safely rounded by clipping only the plugin child. The plugin now has clean square edges.


### Acceptance and remaining boundaries

- Bitwig 6.1.4 uses `CONTENTS/PID…` for initial IDs and
  `CONTENTS/ROOT_GENERIC_MODULE/PID…` for live updates. Only this observed prefix is
  normalized; unrelated paths are rejected. Register ID observers before value observers.
  Model tests cover initial/live aliases and unrelated parameter rejection.
- All 12 live mouse selections matched the natural-minor project key. Computer W/Q
  selections passed too; restored `Am/C → A Minor` and saved.
- 117 Python tests, 4 CTest groups and the real CLAP parameter/GUI/state/MIDI probe passed.
  Evidence: `target/chordlab-minor-sync/`, including the 12-key matrix and keyboard screenshots.
- This round did not repeat the 98-sound audio matrix or physical MIDI/guitar acceptance;
  sound programs and audio routing were not changed.
- One diagnostic shutdown with the sfizz editor open produced X11 BadWindow / plugin-host
  exit 139; root cause remains unconfirmed. Subsequent shutdowns succeeded after closing
  Chord Lab, then sfizz, saving and quitting. sfizz also logs invalid parameter ID 544;
  this is not a claim that all host shutdown paths are fault-free.

## Surge skin selection (2026-10-18)

Installed checksum-verified `Modern Dark Blue` and all nine Andromeda variants into
`~/.Surge XT/Skins/`. Selected the default through `Menu → Skins → Modern Dark Blue`;
`defaultZoom=125` and all other Surge preferences were preserved. Manual Andromeda selection:
`Menu → Skins → Andromeda → Blue / Dub / Green / Orange / Purple / Red / Teal / Wave / Yellow`.
These are visual variants of one skin family, not sound presets or synthesis-engine modes.
Evidence: `target/surge-modern-dark-blue/`.

## Bidirectional project key link (2026-10-18, controller 0.3)

- On controller/project initialization, the saved Bitwig key wins. `C# Minor` maps to
  Chord Lab `C#m/E` (internal major key E); `E Major` maps to the same note collection.
- After initialization, either side can change the key. Plugin edits preserve the host's
  current Major/Minor mode. Same-flush conflicts favor the project. Ordered pending-write
  acknowledgments suppress feedback, including multiple in-flight edits.
- Major and natural Minor only. Other modes pause synchronization with an English notification;
  neither the project scale nor plugin is silently approximated. Returning to Major/Minor
  reinitializes from the host. The plugin still uses its original major-relative degree engine.
- Playback or the shared plugin's Sounding flag defers host-to-plugin changes. The latest host key
  applies when stopped and released. This preserves the existing engine safety lock; it is not
  sample-accurate live key automation. Only the main shared Chord Lab is linked, not the independent
  guitar display instance. Existing Library scope and Project Remotes guards remain required.
- This update is controller-only; the shared CLAP binary, synth patches and audio routing are unchanged.

Validation: 13 migration/controller pytest tests passed; the model covers 24 startup keys,
288 plugin selections, host edits, delayed/multiple echoes, host-priority conflicts, scope/mapping
guards, unsupported modes, transport/sounding deferral and parameter ID replacement/aliases.
Live Bitwig: C# Minor → C#m/E, Db Major → Bbm/Db, plugin C#m/E → E Major, Dorian does not
overwrite the plugin or force the project to Minor; restoring Minor resumes sync. During playback,
a host G Minor change stayed deferred, then selected Gm/Bb after Stop. Controller reload retained
C# Minor. Evidence and pre-change backups: `target/bitwig-key-bidirectional/`.
## Guitar shared input and Grid (2026-10-18, controller 0.4)

The main shared chain is now `Note Receiver → Chord Lab`. It taps `Guitar Frontend` output;
`Channel Map` inside Source FX maps guitar ch 2 to ch 1, with `Mutes Input` off to preserve physical
MIDI. This fixes one source's Note Off cutting off the other source at the same pitch. Plugin binaries
and instrument states are unchanged. The controller supports both the original Chord Lab-only chain
and this specific prefix, not arbitrary preceding devices.

The 98-sound routing matrix, eight synthetic pitches, mixed inputs and Poly Grid loading/audio have
been tested. Real Spark GO recording is deferred at the user's request. The guitar track currently
retains No input / Monitor OFF and requires hardware setup and a real performance check after reconnecting.
See [acceptance details](GUITAR_GRID_ACCEPTANCE.md) for methods, persistence checks, operation and limits.



## Bidirectional diatonic mode sync (2026-10-18, controller 0.5)

This supersedes the Major/Minor-only scope in the 0.3 section; existing safeguards remain.
Supported modes: Major, natural Minor, Dorian, Phrygian, Lydian, Mixolydian, and Locrian.
Host changes select the exact parent-major pitch set in Chord Lab. Plugin changes preserve
Bitwig's current mode and move its tonic. Example: D Dorian → Am/C, then plugin Bm/D → E Dorian.

**Matching pitch sets does not mean matching tonics or chord degrees.** Chord Lab retains
its major-relative degree engine; it does not relabel ii as i for Dorian. This is pitch-set
synchronization, not a complete modal harmony engine. Unsupported scales such as Harmonic
Minor pause both directions without approximation. Returning to a supported mode makes the
host authoritative again, as at startup and simultaneous conflicts. Host updates remain
deferred during playback/held notes; this is not realtime key automation.

Controller 0.5 is installed and reloaded; CLAP binaries and audio routing are unchanged.
Model tests cover 84 startup keys, 1008 plugin selections, 588 host mode/root transitions,
independent interval-table pitch sets, echoes, conflicts, deferral, and unsupported scales.
All 198 selected Python regression tests passed, including the Node controller models.
Live Bitwig checks passed: D Dorian → Am/C, plugin Bm/D → E Dorian, E Phrygian → Am/C,
E Harmonic Minor pausing both directions, and resumption in Minor.
Library was restored to C# Minor / C#m/E, Acoustic Piano, Sustain OFF, and saved.
Evidence and pre-change backups: `target/bitwig-diatonic-sync/`. Physical guitar input and
the 98-sound audio matrix were not rerun in this change.

Bitwig's global key provides a reference for piano-roll highlighting/Snap to Key, Note FX
with Use Global Key enabled, and Grid pitch quantization/scale-degree transposition.
Changing it alone does not transpose all existing MIDI/audio or change Surge timbres.
See [Bitwig 6 release notes, pages 16–19](https://downloads.bitwig.com/6.0/Release-Notes-6.0.pdf).
