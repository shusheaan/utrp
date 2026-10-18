# Bitwig Library: guitar routing and Grid acceptance

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

[中文](GUITAR_GRID_ACCEPTANCE.cn.md) · [Library guide](README.md)

## Scope and status (2026-10-18)

The user explicitly deferred real recording and requested unattended software checks. These results
are not a human performance test and do not establish real-guitar accuracy or end-to-end latency.

- Project: `~/storage/daw/Library/Library.bwproject`.
- Host: native Bitwig Studio 6.1.4, currently Trial.
- Shared binaries: Chord Lab 0.1.10 and Guitar Frontend 0.1.2, unchanged in this pass.
- Library controller 0.4 supports a Note Receiver before the shared Chord Lab.
- Before-project backup and evidence: `target/bitwig-guitar-grid/`.
- Original `~/storage/daw/synth.rpp` remains unchanged and is not deleted.

## Routing

```text
Keystation / All ins ──────────────────────┐
                                         v
GUITAR - raw detection               Note Receiver → shared Chord Lab
  raw mono audio                       ^                   |
  → Guitar Frontend (MIDI ch 2) ────────┘                   v
  → local Chord Lab (optional display)             selected sound → Master

Note Receiver Source FX: Channel Map, ch 2 → ch 1
Note Receiver Mutes Input: OFF
Computer keyboard → focused shared Chord Lab editor
```

The receiver taps **Guitar Frontend output**, before the local display. Channel Map is nested inside
the receiver's **Source FX**, leaving the physical keyboard path and velocity unchanged. The main
shared chain has only `Note Receiver → Chord Lab`.

### Why Channel Map is required

The same-pitch test exposed premature releases: guitar ch 2 and computer ch 1 were merged by the
destination track's All→1 mapping *after* Chord Lab. Either source's Note Off could stop the other.
Different-pitch tests alone did not expose this.

Mapping received guitar notes to ch 1 *before* shared Chord Lab lets its ownership logic merge them.
Either release order keeps the remaining owner sounding; only the final release ends the note.
Overlapping notes retain the first Note On velocity and do not retrigger the envelope on every input.

### Dry guitar and effects

Keep Guitar Frontend first in the guitar audio chain, before reverb, chorus or amp effects. Later
effects cannot influence detection. Software cannot undo distortion/reverb already baked in by
Spark GO, so use a sufficiently clean hardware preset too.

Spark GO is currently absent. The guitar track retains **No input / Monitor OFF / fader −∞**; the
computer microphone was not substituted. Detected MIDI leaves through Note Receiver independently.
After reconnecting, select the correct mono input, enable monitoring and check dry levels. Hardware
connection alone is not acceptance. Configure audible guitar monitoring and downstream effects
separately rather than enabling uncalibrated dry audio.

## Automated acceptance and evidence

1. **Sound routing:** select each of 98 sounds, send MIDI 60 at velocity 80 through the shared track,
   verify destination audio, exclusive activation, arm and Monitor ON. `all-sound-routing.json` is
   the initial matrix; `all-sound-routing-reopened.json` is the separate post-save/reopen matrix,
   whose completed count is authoritative for that pass.
2. **Synthetic audio end-to-end:** temporary Test Tone → Guitar Frontend → receiver/channel map →
   shared Chord Lab → Acoustic Piano. E2/A2/D3/G3/A3/D4/A4/E5 all produced the exact MIDI pitch,
   velocity 90 and instrument audio. `bitwig-synthetic-pitch.json` is the post-channel-map result.
3. **Detection and mixed input:** Detect OFF stops output; ON resumes. Different computer/guitar
   pitches coexist. Same-pitch E3 passes both release orders and final release.
   See `detector-*.json`, `mixed-*.json`, `same-pitch-fixed-*.json`.
4. **Computer keys:** held C with G advances the voicing; V restores it; release leaves no Note On.
   Space changes the Sustain indicator red→green→red. See `live-keyboard.json`, `sustain-on/off.png`.
5. **Key sync:** plugin Q → A Minor; host C# Minor → plugin C#m/E. Finally restored C# Minor.
   See `key-sync-*.png/json`. Only the shared instance participates, not the local guitar display.
6. **Grid:** a temporary `TEST - Grid` track loaded Poly Grid, produced audio from MIDI 60
   (VU 9147/16384), and opened its modular editor. See `grid-loaded.json/png`, `grid-editor.png`.
   This is a device smoke test, not a completed ambient patch.
7. **Software regression:** 134 pytest cases; Chord Lab CTest 4/4; Guitar CTest 2/2 and UBSan 2/2.
   Installed-binary host probes also exercise metadata, state, reset, boundaries and MIDI behavior.
8. **Persistence:** saved, closed and reopened the project; checked the shared chain, nested 2→1,
   Mutes Input OFF and shared MIDI→piano audio. Compared to the before-project, 95 Surge and two
   sfizz state entries are byte-identical. These are deduplicated state-file counts, not track counts.
   The shared Chord Lab state entry may receive a new identifier.

### Interpretation limits

- `playingNotes()` represents Note On/Off, not CC64-held acoustic tails. Sustain does not require
  this list to remain nonempty after releasing keys.
- Bitwig direct-parameter observers did not update the plugins' read-only meters/Sustain state
  live in this pass. Detection is validated using received pitches, audio and UI indicators instead.
- Initial harnesses with incorrect assertions are retained as diagnostic evidence, not passing results.
- Pure test tones are not real-guitar harmonic/noise/slide tests. No dyad, triad or strum claim is made.
- Audio evidence is host metering, not a subjective listening review. Speaker links were initially
  disconnected, but after reopening the project the right output was found recreated as `out3`
  instead of `out2` and automatically reconnected. Continuous silence is therefore not claimed.
  Final routing is `out1 → FL`, `out3 → FR`. Future unattended tests should use a dedicated silent
  output rather than rely on a one-time PipeWire disconnection.
- Surge switching still logs `failed to activate audio ... bus`; the corresponding sounds pass
  actual output tests, but this is not a zero-error-log claim. `engine-log-tail.txt` retains evidence;
  the shared Surge installation was not upgraded or replaced. EOFExceptions from temporary TCP
  probe short connections are recorded separately and are not treated as instrument crashes.

## Operation and deferred human tests

Final cleanup: the post-save/reopen matrix passed **98/98** again. `Test Tone`, `TEST - Grid` and
temporary `Library Probe` were removed; port 19671 is closed, no test clip or held Note On remains,
and transport is stopped. Restored Acoustic Piano, C# Minor, Sustain OFF and the original output
device, with computer focus on Chord Lab. Machine-readable summary:
`target/bitwig-guitar-grid/acceptance.json`. No unattended human audio recording was made.

1. Open Library and select a sound. The controller enables that sound and opens its editor plus Chord Lab.
2. Physical MIDI needs no editor focus. Computer chords require clicking Chord Lab so the right
   Keyboard indicator is green.
3. G/V work while holding chord keys. Space toggles Sustain; semicolon resets voicing. Focused
   plugin Space is not the DAW Play shortcut.
4. Reconnect guitar and validate exact octaves, onset/release and perceived latency before polyphony.
5. The fretboard shows all positions for the same MIDI pitch, not the actual string/fret used.
6. Disable `Exclusive audition + editors` in Controllers before a normal multi-track arrangement.

Still deferred: Spark GO reconnect/dry input, physical Keystation keypresses, actual guitar registers,
repeated notes, fast transitions, noise rejection and perceived latency. None is marked passed.

## The Grid installation

Grid is native to Bitwig; this machine's Trial loaded it without an additional VST/CLAP install.
Poly Grid makes instruments, FX Grid processes audio, and Note Grid generates/processes notes.
These are device roles, not three external plugin packages. The Essentials content pack is not an
Essentials license. Check Grid entitlement after Trial; current Trial availability does not prove the
old 16-Track license includes it. See the
[official Grid device guide](https://www.bitwig.com/userguide/latest/the_grid_devices/).

Next learning step: oscillator → envelope → output in Poly Grid, then filter, slow LFO, randomness
and scale quantization. Do not leave a large unverified experimental patch in Library yet.
