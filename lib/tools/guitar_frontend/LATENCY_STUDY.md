# Mono-first latency and octave regression screening

[中文](LATENCY_STUDY.cn.md)

## Goal and decision, 2026-10-17

The user accepts dropping unreliable dyad/triad support: prioritize correct single-note pitch/octave, then reduce latency. Abstention is allowed but misses must be reported. Describe the requested string/fret and wait for readiness before recording user performances.

**Offline configurations only: production defaults/plugin were not changed, installed or restarted. No accelerated candidate is approved for deployment.** Production remains 0.1.1. The reported seventh/eighth-fret issue still awaits a labeled real recording.

## Method

The same algorithm is built with six fixed frame/hop/stability configurations from `latency_study.toml`, each with its own generated header, detector tests and replay executable, not a CLAP. Compilation failures abort; test failures are retained explicitly.

| Frame/hop/stability (ms) | Existing detector suite | Maximum synthetic single-note onset |
|---|---|---:|
| 64/8/24, baseline | Pass | 80.25 ms |
| 48/8/16 | Fail: extra note in continuous melody | 56.17 ms (pitch matrix only) |
| 48/4/8 | Fail: extra note in continuous melody | 52.15 ms (pitch matrix only) |
| 40/4/16 | Pass | 52.15 ms |
| 40/4/8 | Pass | 44.13 ms |
| 32/4/8 | Pass | 36.10 ms |

The suite includes 510 pitch/waveform/rate cases, 45 targeted virtual-low-note cases, rejection, continuous melodies and repeated picking. **Passing these tests does not certify real guitars or end-to-end latency.**

## Historical recording rejects naive window shortening

Replay the known problematic 27.9–29.2 s interval of the previous Spark recording. This is mixed/ringing audio rather than labeled pure mono; a mono-only product should still avoid inventing absent low notes when exposed to it.

These percentages describe `current` output after stability/release handling, not raw `observed` frame candidates. Hops differ, so compare fractions rather than counts. This is not whole-recording accuracy.

| Configuration | Output states with false E2/A2 | No-note states |
|---|---:|---:|
| 64/8/24 | 0% | 24.69% |
| 40/4/16 | 19.69% | 7.69% |
| 40/4/8 | 20.92% | 7.08% |
| 32/4/8 | 25.54% | 5.23% |

Baseline raw `observed` still contains one A2 frame that stability prevents from reaching output. The prior zero-error result refers to `current` in this particular interval, not perfect raw candidates. Short windows increase errors; release can also prolong them. Reducing Stability alone is not a solution.

## Update: Spark GO A3 capture (2026-10-17)

The user confirmed repeated D-string fret-7 notes at the beginning and uncontrolled playing at the end. This session evaluated production 0.1.1 without algorithm changes, deployment, or a REAPER restart.

- The first 38.2 seconds include attacks, sustains, damping and gaps: 3785 output hops at A3, 975 without a note, and 7 at A#3. No low-octave output occurred. Intentional silence is included, so the no-note count is not a false-negative rate.
- Twelve manually selected sustain interiors contain 2601 hops, all MIDI 57 for both `current` and `observed`. This passes those intervals only, not every transient or other pitch.
- Brief A#3 output occurs at 12.800–12.832 and 32.080–32.104 seconds. Adjacent rising zero crossings in the original waveform also shorten beforehand, corresponding briefly to roughly 233–248 Hz before returning to 220 Hz. This does not establish a fabricated pitch jump; damping/release transients and waveform changes require distinction. Zero crossings are not precise pitch ground truth either.
- Ten reviewed separated attacks measure roughly 60–86 ms from a raw 5 ms RMS block crossing −48 dBFS to offline `current=A3`. This threshold is not the physical pluck onset and excludes interface, host and UI latency. It does not establish MIDI-keyboard-like responsiveness. Automatic threshold candidates also include damping rebounds and already active notes; these were not treated as new attacks. The first note was already sounding at capture start and is excluded from latency measurements.
- The tail contains actual approximately 82 Hz energy and harmonics; the user confirmed uncontrolled playing. Do not score the entire recording as all-A3 ground truth.

**The sampled A3 sustain pitch/octave check passes. Transient display behavior and low-latency acceptance remain incomplete. G-string fret-7 D4, continuous melodies, dyads and triads are not certified by this test.**

Capture used `pw-record --target 0` with `node.autoconnect=false`, followed by an explicit `pw-link` from Spark GO. Recorded links exclude the computer microphone. The recorder returned 1, but the WAV decodes fully to 60 seconds of 48 kHz mono float32, peak −11.36 dBFS, with no full-scale clipped samples. Preserve the anomalous exit status rather than reporting normal process completion.

Evidence under `target/guitar-a3-validation/`: `a3-spark-02.wav`, `routing-02.txt`, `baseline-02.csv`, and `initial-analysis-02.json` (spectra, intervals, threshold method and caveats). WAV SHA256: `c8e2318582c00cd61b39fb66ecf86918cd3adcf58575acf17ef109ef0beb7cce`. `live-observation-02.tsv` started later and is not precisely synchronized, so it cannot measure end-to-end latency.

The baseline detector suite was rerun successfully: 510 pitch/rate/waveform combinations, 45 ringing-string virtual-low regressions, rejection cases, continuous melodies and repeated plucks. These remain synthetic tests, not substitutes for real-guitar acceptance. Installed Guitar Frontend and Chord Lab SHA256 hashes are unchanged. Next: validate D4 and evaluate transient display behavior without blindly delaying all notes to hide two transients. Previously failed short-window variants remain undeployed.

## Next steps (original capture plan; A3 progress above)

- Once the user is ready, record standard-tuning fourth string, seventh fret: A3 / 220 Hz / MIDI 57. Isolated plucks, other strings muted, clear attacks and complete damping. Compare raw spectrum, frontend MIDI and actual Chord Lab activations.
- Then third string, seventh fret: D4 / MIDI 62. Equivalent pitches on other strings' higher frets are not octave errors; pale chord-reference dots are not input detections.
- Do not shorten production windows based solely on synthetic success. No zero-error or keyboard-equivalent response promise.

## Reproduction and evidence

```sh
python lib/tools/guitar_frontend/latency_study.py \
  lib/tools/guitar_frontend/latency_study.toml target/guitar-latency-study
python -m pytest -q lib/tools/guitar_frontend/test_latency_study.py \
  lib/tools/guitar_frontend/test_configure.py
```

`target/guitar-latency-study/results.json` retains source hashes, configurations, exit codes and full output. `real-replay.json` separates `current` from `observed`; per-configuration CSVs retain the trace. Recording SHA256: `acab13bbe18672c6c1e14b4bd3413d850cb5e98e86630d5703cfed15d95c9b3a`. Replay stdin is native float64 mono at 48 kHz, not WAV bytes. Python configuration/study-tool tests: 28 passed.
