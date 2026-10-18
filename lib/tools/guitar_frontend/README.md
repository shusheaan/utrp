# Guitar Frontend 0.2.1 — monophonic only

2026-10-18: real playing rejected the dyad experiment, including fifth/octave failures. Mode and the second-note meter are removed. Dyad runtime sources are retired from the product; offline research remains historical, not acceptance evidence.

- Keep the verified 0.1.2 mono detector and 64 ms / 8 ms / 24 ms settings. Accuracy takes priority over unproven latency reductions.
- Current project: `~/storage/daw/Library/Library.bwproject`. Detect remains available. Guitar-derived MIDI is display-only in Chord Lab, not layered synthesizer playback.
- Load v1 and experimental v2 states; either former Mode restores as mono while preserving other parameters. Save v1 states.
- No guarantee of perfect recognition. Chords, overlapping strings and strums are unsupported.

## Historical notes (older version/deployment statements below are superseded)

# Guitar Frontend 0.2.0 — Mono / experimental Dyad

Current version: [Mode switch and testing](MODE_SWITCH.md). Mono is unchanged; Dyad is explicit, not automatic arbitration. The 0.1.2 sections below are historical.

# Guitar Frontend 0.1.2 — monophonic prototype

## Dyad experiment (2026-10-18; production unchanged)

Latest: [dyad speed and mono-safety regression](DYAD_SPEED.md). First confirmation on the D/G
development recording is now 56–90 ms. Offline candidate only; production mono remains unchanged.

Added a [conservative offline dyad study](DYAD_STUDY.md): equal-strength signals across standard-tuning frets 0–24,
independent harmonic evidence and causal onset/release checks. Production CLAP remains monophonic 0.1.2.
The dyad experiment is not installed in Bitwig; triads, full-fretboard real-guitar accuracy and live latency are not accepted.

[中文](README.cn.md)

**2026-10-18 update:** [Bitwig / UTRP wrap-up](../bitwig_library/WRAPUP.md).
Bitwig loading, synthetic monophonic input and shared MIDI routing are now validated,
superseding the earlier untested-in-Bitwig entry below. Real Spark GO performance remains
pending; the monophonic prototype limitations are unchanged.

## 0.1.2 deployment and controls (2026-10-17)

Deployed and restarted in `Guitar Lab.rpp`. The new **Guitar Lab** application-menu entry uses the existing `/home/shu/.local/bin/reaper` routing launcher and opens this project. The ordinary launcher's default remains `synth.rpp`; the library was not changed. Connect Spark first. Run the Guitar Lab entry again after device reconnection to refresh routing. Missing Spark leaves inputs disconnected instead of falling back to the computer microphone. Directly invoking the REAPER binary bypasses this correction and was observed to auto-connect the microphone to input 1.

Toggle guitar-to-MIDI using the first Guitar Frontend parameter, **`Detect (mono prototype)` → `On (mono)` / `Off`**. Off releases detected notes without muting Spark direct monitoring. The production-host toggle check passed and On was saved. Chord Lab's Keyboard button is unrelated to guitar detection.

The dedicated analysis track has no Input FX, receives or media items; Guitar Frontend is its only ordinary FX, fed by hardware input 1. Future REAPER amp/distortion/reverb/chorus effects belong on a **separate audio track reading the same hardware input**, never before the detector. This isolates REAPER effects, not effects already embedded in Spark's USB stream; keep Spark clean upstream.

### Nearby-low spectral leakage fix

A D4 capture produced false G2 at 17.712–17.736 seconds: window leakage from a real weak 82 Hz component incorrectly supported the approximately 98 Hz candidate. A local spectral-peak check now guards fundamental support, retaining high-pitch estimator tolerance via `spectral_peak_cents=30`. No additional buffering or timing-window change was introduced; latency was not reduced.

- D4 13.9–45 s: wrong output 3 → 0 hops; no-note output 219 → 219.
- A3 0–38.2 s: adjacent-semitone output 7 → 0 hops; no-note output 975 → 987, an extra 96 ms. Not every transient pitch change is necessarily an estimation error.
- Historical ringing interval: unchanged output of E4 for 122 hops and no note for 40. Raw candidates can still be wrong; this is not a zero-error guarantee.
- Release and UBSan CTest each pass 2/2: original 510 pitch cases, 45 ringing cases, 160 new nearby-low/phase/rate cases, and 40 CLAP-host combinations. Python configuration/study tests pass 31 cases.
- Production REAPER loaded the new binary; raw-input topology, Detect Off/On and saved readiness were checked. This is not a fresh exhaustive DAW pitch-routing certification. Polyphony, Bitwig and MIDI-keyboard-like latency remain unaccepted.

Evidence and pre-restart backups: `target/guitar-d4-validation/`. Previous acceptance is retained as `acceptance-0.1.1.json`; `acceptance.json` describes 0.1.2. Historical zero-low-output counts refer to stable `current`, not raw `observed` candidates; the latter still contain an A2 candidate rejected by stability.

Standalone CLAP: clean guitar audio → MIDI channel 2 → existing Chord Lab. No changes to Chord Lab's engine or keyboard mapping; detection does not depend on REAPER or JSFX. Uses the host's generic parameter editor.

## Scope

- Single-note melodies/scales and non-overlapping arpeggios (mute the previous note first).
- MIDI 38–88 (D2–E6), A4=440 Hz, rounded to semitones; fixed velocity, no pitch bend/MPE or dynamics estimation.
- Existing Chord Lab highlights every visible string/fret position matching the exact MIDI pitch; actual string/fret cannot be inferred.
- Guitar detection does not require window focus. Computer-keyboard Chord Lab performance still does.
- Stereo dry audio passes sample-for-sample unchanged; analysis uses one selected channel.

**Not supported:** simultaneous two/three-note input, six-string strumming, or ringing/overlapping arpeggios. These can produce false fundamentals, harmonics or unstable notes. Same-note retrigger uses an energy heuristic, not guaranteed pick segmentation.

## Local trial project

`/home/shu/storage/daw/Guitar Lab.rpp`, separate from `synth.rpp`:

```
Spark GO capture_MONO → REAPER input 1
  Track 1: Guitar Frontend (normal FX, audio input, armed + monitored)
    └─ MIDI-only send → Track 2: Chord Lab (normal FX, display only, no synth)
```

Bypass Amp and all FX in the Spark app where possible. Track 1's Master send is off to avoid duplicate software/direct monitoring. Listen to Spark's direct guitar sound; this project does not play a piano instrument from detected MIDI.

Check `pw-link -l` for `capture_MONO → REAPER:in1`; never use playback `monitor_FL/FR` as input. On this machine startup initially connected the computer microphone instead; that connection was corrected. A project file cannot guarantee PipeWire selects the same hardware after reconnect/restart. MIDI track sends feed normal FX, not destination Input FX.

## Controls

| Parameter | Default | Meaning |
|---|---:|---|
| Detect | On | Disable detection and release MIDI; dry audio remains unchanged |
| Gate | -48 dBFS | Raise for noise rejection, lower for quiet notes |
| Confidence threshold | 0.88 | Higher is stricter but may miss notes |
| Stability | 24 ms | Higher suppresses brief pitch changes but increases delay |
| Release | 40 ms | Detection hold time; not a Sustain pedal |
| MIDI velocity | 90 | Fixed MIDI velocity, not dry guitar gain |
| Analysis input | Left | Channel to analyze; current mono input uses Left |
| Detected MIDI note / Input level / Pitch confidence | Read-only | Note, level, periodicity confidence (not probability of correctness) |

Input level is block peak dBFS; Gate uses filtered frame RMS. Diagnose missing input/routes before lowering Gate.

## Validation and limitations

- DSP: 510 synthetic pitch/rate/waveform combinations at 32/44.1/48/96/192 kHz. Worst measured synthetic attack about **80.25 ms**, release **95.15 ms**, before hardware/host buffering. This is not a real-guitar latency guarantee. Dry audio has no additional buffering delay.
- Independent CLAP host: 40 rate/block/float32/float64 combinations, bit-exact audio, MIDI, rejected-event retry, reset/disable, parameters, partial state streams, invalid states and instance isolation.
- Isolated REAPER: 14 synthetic pitches, 28 MIDI on/off events matching before/after Chord Lab via a MIDI-only send.
- Hardware: non-silent Spark input and detected notes observed. **Open-string accuracy, repeated picking and real noise conditions still require labeled human playing; not certified.**
- Bitwig: standard CLAP audio/note/params/state interfaces without REAPER runtime dependencies, but **not loaded/routed/recorded in Bitwig yet**. Audio-to-MIDI device-chain or cross-track Note Receiver routing requires host validation; REAPER projects do not transfer directly.

Detection uses low-pass filtering, decimation and YIN-style periodicity analysis with fixed-capacity buffers. No allocation, file I/O or mutex in the real-time path. This is not a polyphonic transcription model and uses no training data.

## 0.1.1 false-low-note correction

The captured Spark clip reproduced a shared-period error: ringing E4/B3 energy could be interpreted as E2/A2 by the original single-pitch detector. The new spectral check rejects a candidate with insufficient fundamental energy, then checks supported higher harmonics. Ambiguous frames return no observation rather than inventing a low note; normal release handling still applies. This remains **one dominant note**, not polyphonic transcription. Missing-fundamental or heavily processed sounds can still be rejected or misidentified.

For the specific 27.9–29.2 s regression interval (162 observations): E2/A2 errors fell from **105 to 0**; the new result was E4 in 122 frames and uncertain in 40. This is a targeted recording regression, not a general accuracy guarantee. The original 510 synthetic cases, 45 new ringing-note cases, 40 independent-host cases and 14-pitch isolated REAPER chain passed; related Python regressions: 116 passed.

The ordinary Confidence threshold governs initial YIN selection. Spectral rescue has a separate compiled threshold (`subharmonic_confidence = 0.60`), so its reported confidence can be below the ordinary 0.88 setting. It is periodicity evidence, not a probability. Configuration also exposes `fundamental_power_ratio` and `spectral_margin` in `defaults.toml`. No analysis/stability waiting time was added; the latency limitations above remain.

`replay_clip` is an offline diagnostic accepting native float64 mono samples at 48 kHz on stdin and emitting CSV observations. It is not part of the plugin. See `acceptance.json`; prior results are preserved in `acceptance-0.1.0.json`.

## Build

CMake ≥3.22, C++17, Python ≥3.11 and the pinned CLAP headers referenced by `../chordlab_clap/dependencies.toml`. Python is build-time only.

```sh
cmake -S lib/tools/guitar_frontend -B target/guitar-frontend-build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCLAP_INCLUDE_DIR="$PWD/target/chordlab-clap-build/deps/clap-juce/clap-libs/clap/include"
cmake --build target/guitar-frontend-build -j2
ctest --test-dir target/guitar-frontend-build -V
python -m pytest -q lib/tools/guitar_frontend/test_configure.py
```

Install `target/guitar-frontend-build/Guitar Frontend.clap` into `~/.clap/` on Linux, then rescan/reload. Editing `defaults.toml` requires rebuilding; saved project parameters override defaults. The generator rejects unknown fields, NaN/Inf, invalid ranges and oversized windows.

`stage_test.py`, `reaper_test.lua` and the test JSFX are isolated-host fixtures, not production library effects. `live_setup.lua` only accepts an empty project named `Guitar Lab.rpp`.

Additional checks: both UBSan CTest targets passed. ASan could not complete because the system AppProtection preload conflicts with runtime initialization; this is not a pass. See `acceptance.json` for scope.

## Subsequent mono-first experiment

The user accepts dropping unreliable polyphony to prioritize single-note pitch/octave correctness and latency. Six offline timing variants revealed continuous-melody or recorded-audio regressions; none was deployed. See the [mono latency study](LATENCY_STUDY.md).
