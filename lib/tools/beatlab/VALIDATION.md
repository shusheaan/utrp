# Prototype validation — 2026-10-20

[中文](VALIDATION.cn.md) · [Usage](README.md)

## Latest: in-plugin four-bar recording (0.3.0)

- Added `plugin/recorder.h/.cpp` and `plugin/waveform.h`. C++ handles host audio I/O; Rust still owns analysis/classification/MIDI computation.
- Once/Loop, four-beat count-in, exact four-bar capture, last-complete-take retention; Stop discards an unfinished tail.
- Recorder tests cover count-in/click exclusion, once/loop, stop boundaries, tempo/rate/meter changes, invalid input and fractional timing.
- Synthetic GUI/processor end-to-end: stopped host transport with input callbacks, input R, fractional host BPM, automatic analysis, four-bar MIDI and source PCM state recovery; saving before the UI timer still captures the completed take.
- 14 Rust tests and Clippy, CTest `clap`/`recorder`, GUI/FFI pass. Standalone Recorder UBSan passes.
- ASan incomplete: environment reports runtime link-order error; do not claim all sanitizers passed.
- Visually checked synthetic screenshot `/tmp/beatlab-four-bars/recording-ui.png`: waveform above grid, four bars and recording controls visible.
- New Bitwig instance with real microphone/audible count-in/latency remains untested. Synthetic tests are not real complex beatbox accuracy acceptance.
- Local clock follows host BPM; no DAW transport start or arrangement-phase alignment. Acoustic click bleed and hardware latency need live verification.
- Direct MIDI clip writing, live MIDI output and reusable Sound Set templates remain pending; output uses `.mid` export after recording.
- No commit/push; deployment and Storage snapshot results are recorded at wrap-up.

### 0.3.0 deployment

Atomically installed at `~/storage/daw/UserData/.clap/Beat Lab.clap` and `~/storage/daw/Tools/BeatLab/Beat Lab`.
Previous binaries: `~/storage/daw/BeatLab/Backups/20261020T192935Z-recording-v030/`.
CLAP SHA-256: `648a5ae262d15a081f946e5f88166ad1defa4d02997fff18eea04bbff9ffeefd`.
Bitwig was not restarted and Library was not edited. Existing host instances need reloading; deployment is not live acceptance.


## Bitwig clip drag probe — integration still pending

- Bitwig 6.1.4 / Sway / XWayland, disposable project and synthetic WAV; no user recording or Library edits.
- Added manual `drop_probe [existing-audio-file]`: JUCE `FileDragAndDropTarget`, accepts all file types, opens no audio device.
- Positive controls: probe-generated WAV drag into Bitwig succeeds; WAV drag back into the probe produces `DROP`.
- Arranger clip header, audio-event waveform and header drags to the standalone probe yielded no file payload. Pressing B during drag also yielded none.
- This tests standalone file payloads, not an embedded CLAP GUI or every possible host-transfer path. Direct clip drag is not verified.
- Embedded plugin drag or a host bridge still requires investigation. A raw sample file is not equivalent to a trimmed, stretched or offset clip.
- Disposable project discarded, probe closed, Library restored. New plugin not deployed; no commit/push.



## Latest: dense four-bar grid (local build, not deployed)

- 14 Rust tests and clippy pass; quantization boundary coverage now includes 8/12/16 subdivisions per beat.
- CLAP/Standalone build, CTest CLAP and GUI/FFI pass.
- GUI: 64 events analyzed over four bars, MIDI ends at tick 15360 (960 PPQ).
- Coordinate/insertion roundtrips pass for five subdivisions and four/two/one-bar views.
- All 256 same-lane markers are individually addressable. View/zoom/pan do not mutate pattern; Off retains microtiming.
- Wrong-length input reports an error without replacing the previous pattern; valid four-bar input works afterward.
- Visually checked `/tmp/beatlab-four-bars/ui.png`: four bars and all beat labels visible without overlap.
- Real dense beatbox accuracy remains untested; 45 ms onset separation unchanged. Sound Set templates and host clip integration remain pending.
- Not deployed or committed/pushed; installed user plugin unchanged.


## Latest: simplified four-category local build (not deployed)

- Offline Rust tests: 3 unit + 11 integration = 14 passing; clippy with warnings denied passes.
- CLAP/Standalone Release build passes. Current CTest contains `clap` only; capture and its tests were removed.
- GUI/FFI passes: no Record/Stop/Save Take, four mappings, automatic WAV drop analysis, `.bwclip` rejection,
  safe v1 Review migration, state round-trip, no default feedback and independent JUCE MIDI decoding.
- Added four synthetic sound categories through audio→analysis→four MIDI notes, D export/Review omission and schema boundaries.
- Visually checked `/tmp/beatlab-v2/ui.png`: four categories plus Review, four mappings, no overlap/clipping.
- Does not force four groups for fewer sounds. Real beatboxing classification accuracy is not established.
- **Not deployed; Library test tracks not recreated. Bitwig project clip input and MIDI clip drag-out/insertion remain pending.**
  MIDI file export is a development outlet, not the requested finished workflow. No commit/push.

Earlier prototype acceptance remains below as history; capture behavior no longer describes current sources.

## Passed

- Independent SHA-256-verified source preparation; Rust static library, JUCE Standalone and CLAP Release builds.
- `cargo test`: 2 unit tests and 8 integration tests.
- `cargo clippy --all-targets -- -D warnings`.
- CTest `capture`: count-in, exact duration, stop, jumps, tempo changes, invalid time signatures, standalone clock.
- CTest `clap`: dynamic discovery, unique ID, initialization, audio ports, activation, processing, mute and shutdown.
- Offscreen UI/FFI: Demo callback, asynchronous analysis producing 32 events, state roundtrip, corrupt-state rejection.
- Nonzero input is muted by default; zero-channel buffer is safe.
- Independent JUCE decoding of Rust MIDI: 32 Note Ons, channel 10, PPQ 960, two-bar end at 7680 ticks.
- Visual inspection of offscreen screenshot: gray palette, capsule controls, English labels and colored notes/white rings without obvious clipping or overlap.

Synthetic onset regression covers **12 sample-rate/BPM combinations** (8/44.1/48/96 kHz × 60/120/180 BPM), 32 events each, onset errors below 12 ms. This is neither live latency nor a real beatbox accuracy guarantee.

Other Rust tests cover silence, nonfinite audio, invalid settings, JSON roundtrip, state field validation, omitted Review events, quantized note collisions, quantization boundaries and loop length.

## Not yet accepted

- Actual microphone capture and host recording-clock validation in Bitwig; the Demo analysis/export/import chain is now tested.
- Actual REAPER loading.
- User beatbox recall, false positives and clustering accuracy.
- Physical microphone levels, click bleed and device reconnection.
- Audio-inclusive session persistence, live MIDI output, direct DAW clip writing and MIDI drag-out are **not implemented**.

The minimal CLAP smoke host is not Bitwig certification. This is a built and automatically tested prototype.

## Bitwig Library demonstration — 2026-10-20

- Loaded Beat Lab CLAP in Bitwig Studio 6.1.4; added the Audio track `beat lab - input` and Instrument track `beat lab - drums` to the existing Library.
- Actual plugin Demo produced 64 events at 120 BPM, 4/4, four bars. Exported through the real MIDI dialog and imported into a four-bar looping Clip Launcher clip.
- Drum Machine uses the installed `Legend 808 Normal Kit`. Its layout is not GM: A/B/C map to MIDI **36/37/38**, its Kick/Snare/Hi-Hat pads. Instrument names in Beat Lab's menu are GM hints, not host pad names.
- Saved, closed and reopened Library: clip, drum kit, Beat Lab pattern and mappings survived. Raw audio is not included in plugin state; use Demo or import WAV again for Hear.
- Verified nonzero stereo output without clipping. Final four-second WooAudio monitor capture peaked at approximately **−28.50 dBFS** on both channels. This is a signal measurement, not a listening assessment.
- Spark GO is currently absent. Bitwig was configured for HDMI, and its right output returned to HDMI after reopening. Selected the available WooAudio device in Settings → Audio and rechecked stereo output. **Spark GO hotplug switching remains unverified**: the existing routing policy hardcodes out1/out2, while rebuilt ports reached out5/out6; this needs separate remediation/acceptance.
- Playback is stopped. The input track has No input; neither microphone recording nor real beatbox accuracy is accepted. Existing tracks/groups remain; piano gain restored to −10 dB.

Project: `~/storage/daw/Library/Library.bwproject`. Pre-change backup: `~/storage/daw/Backups/library-before-beatlab-20261020T180543Z/Library.bwproject`.
MIDI: `~/storage/daw/BeatLab/Examples/library-808-demo.mid`; the original GM mapping is `library-demo.mid`.

To listen, click the triangle on `beatlab-808-demo` in `beat lab - drums`; use the top Stop button to stop. Mapping edits require MIDI re-export and clip replacement: there is **no live MIDI/clip synchronization** yet. Do not insert Beat Lab into existing guitar/synth chains: it mutes passthrough audio by default.

## Reproduce

In addition to README test commands, offscreen UI testing requires a graphical session but opens no visible window:

```sh
cargo run --offline --manifest-path lib/tools/beatlab/Cargo.toml --example demo -- /tmp/beatlab-demo
lib/tools/beatlab/build/gui_test /tmp/beatlab-demo/demo.json /tmp/beatlab-ui.png
```

Next, record two bars of separated low/plosive/noisy mouth sounds at similar volume without overlap. Label onsets/classes before testing dynamics, rolls and longer recordings.

## Microphone connection update

The previous No input state is resolved: `beat lab - input` now uses the `beat lab mic` named bus, Arm and Auto Monitor, fed by the SF-558 USB microphone. Nonzero plugin input was observed; the dedicated reconnection policy is deployed and tested. Passthrough is still muted. Record was not started; real beatbox capture/analysis awaits the user.

## 2026-10-20 newly created Beat Lab track input check

The user-created `Beat Lab` Audio Track had `No input` and was not armed. SF-558 and the PipeWire links to `beat lab mic L/R` already existed. Selecting `beat lab mic` and arming through the GUI changed the v0.3 plugin Input from silent to approximately −37 to −31 dBFS while host transport remained stopped. Recording was not started; real beatbox recognition remains unverified. Library was saved; the previous on-disk project is backed up at `~/storage/daw/Backups/library-beatlab-input-20261020T195821Z/`. No plugin code, routing policy, or preferences changed.

## v0.3.1: sparse real-take detection fix (2026-10-20)

- User take: 48 kHz, 120 BPM, 8 seconds; old detector found 8 onsets. Mean +0.00812 and 20th-percentile RMS −43.22 dBFS caused `max(Gate, floor * 3)` to impose −33.68 dBFS. Lowering Gate from −36 to −48 had no effect.
- Subtract whole-take DC mean from the analysis copy, preserving source PCM, audition and sample indices. Remove the hidden whole-take floor override; retain rising-edge and 45 ms spacing rules. Gate now directly controls the RMS threshold and persists in host state (legacy default −36; invalid types/ranges rejected).
- Offline comparison on identical source PCM: Gate −36 / −42 / −45 / −48 gives 12 / 23 / 33 / 53 candidates; −45 includes one Review event. More candidates do not establish accuracy: no ground-truth annotation, recall or classification score is claimed. −48 has increased noise risk.
- Added multi-rate DC-bias invariance, quiet-hit Gate control, continuous-background Gate behavior and constant-bias/stationary-noise regressions. Rust 17 tests and clippy passed. Private source audio stays in Storage/temporary files, not Git.

Deployment check: CTest 2/2 and GUI/FFI/state/recording regressions passed, including Gate persistence and invalid-value rejection. With user authorization, Bitwig was reopened; the same Library take produced 33 candidates at −45 dB (one Review). Inspection of the saved project plugin state confirmed identical original PCM, gate_db = −45 and all 33 events. All 10 Storage links passed. Old binaries/project/original WAV: `~/storage/daw/BeatLab/Backups/sparse-fix-20261020T200424Z/`. Actual classes and missed/extra candidates still require user listening.
