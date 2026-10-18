# Conservative 1–3-note experiment

[中文](CONSERVATIVE.cn.md)

## Goal and delivery boundary

Show supported single notes, dyads and triads; abstain rather than guess or hold stale notes; suppress strumming. The first user-labeled test is standard-tuning **open D3/G3, MIDI 50/55**.

`conservative.py` is an **offline Python experiment, not a delivered CLAP feature**. Production Guitar Frontend remains 0.1.1, single dominant note. It has not been replaced or restarted and does not implement this experiment's group-rejection policy.

Absolute correctness cannot be guaranteed from mixed audio: two independent sinusoids at f and 2f can produce the same waveform as one harmonic sound. Six strings can also contain only three pitch classes plus octave duplicates. A three-note estimate is not evidence that only three strings were played; confidence is not correctness.

## Experimental rules

- No D/G label, selected-chord or key restriction: all MIDI 38–88 candidates remain available.
- Fixed causal 128 ms Hann windows, 8 ms hops, interpolated spectral peaks. Require fundamental evidence, at least three independent harmonic peaks, semitone proximity, spectral coverage and tonal concentration. Shared thresholds are in `conservative.toml`, not tuned per fixture.
- Require five stable candidate frames. These thresholds are not calibrated probabilities. Sine-only or missing-fundamental sounds, weak voices and harmonic ambiguity can be rejected or missed.
- Clear simulated output immediately when candidates change or analysis rejects a frame. Window latency still applies: this is not instantaneous physical note-off detection.
- More than three detected independent candidates causes group rejection, latched until sustained quiet. **Underdetection can defeat this protection.** There is no reliable strum/gesture classifier.
- Preserve exact MIDI pitches rather than collapsing octaves; Chord Lab handles equivalent fretboard positions, not inferred string identity.

## Fixed synthetic screening (2026-10-17)

Full evidence: `target/guitar-conservative/screening.json`. Three levels, sine/eight-harmonic timbres. “Ever exactly correct for 20 ms” is a permissive screen, not a whole-case pass.

| Voices | Cases | Ever exact ≥20 ms | Any spurious pitch | Maximum successful set onset latency |
|---|---:|---:|---:|---:|
| 1 | 36 | 18 | 0 | 124 ms |
| 2 | 54 | 21 | 0 | 132 ms |
| 3 | 30 | 9 | 0 | 132 ms |

- Harmonic D, G, D+G and D+G+B fixtures produced the expected sets at all three levels. This is not real-guitar validation or a restricted candidate vocabulary.
- Twelve overlapping-arpeggio cases had no extra pitch, without certifying complete sets or transitions.
- **Three of 24 dense/strummed rejection cases still emitted a three-note set: deployment gate failed.** Example: six-string G chord `[43,47,50,55,59,67]` became `[43,47,50]`. Those pitches exist, but emitting them violates the requested whole-strum suppression rule.
- Many of the 120 cases miss voices or abstain entirely. Zero extra pitches alone is not success. No representative real-guitar validation, calibrated probability, real-time CPU guarantee or Bitwig acceptance exists.
- This experiment is slower than production and does not meet the very-low-latency goal. The 8 ms hop is not end-to-end latency.

## Required next steps

1. Measure labeled user D/G recordings for onsets, offsets, misses, errors and abstention. Add isolated D and G controls, then a labeled triad. Never restrict the candidate set to known answers.
2. Add diverse guitar timbres, level imbalance, semitones, octaves, fifths, detuning, noise, four-to-six-note strums and different onset spacings. Report misses, false notes, incorrectly accepted groups and P50/P95/maximum delay together.
3. Do not deploy before held-out tests pass. Keep the strum failures visible; one successful dyad cannot substitute for acceptance.
4. Only after an engine qualifies: expand C++ single-note `Observation/Update/current` to fixed-capacity sets of at most three notes. Emit MIDI set differences, releasing only this frontend's notes on rejection without affecting computer-keyboard notes. Test backpressure, stop, disconnect, mute, state restore and multiple instances. Preserve dry-audio passthrough and host-independent CLAP interfaces; validate REAPER and Bitwig separately.

## Reproduction

Requires NumPy and Python ≥3.11. No prior PDCT upstream code is embedded or modified.

```sh
mkdir -p target/guitar-conservative
python lib/tools/guitar_poly/screen_conservative.py \
  lib/tools/guitar_poly/conservative.toml \
  lib/tools/guitar_poly/conservative_benchmark.toml \
  target/guitar-conservative/screening.json
python -m pytest -q lib/tools/guitar_poly/test_conservative.py lib/tools/guitar_poly/test_benchmark.py
```

## Current recording status

The first D/G file decodes to 60 seconds, but peaks near −73 dBFS and is mostly zero: it is not usable pitch-accuracy evidence. Spark input is unmuted at 100% gain and remains connected to REAPER. Whether the user played is awaiting confirmation; no real-dyad success is claimed. The recorder returned exit code 1 despite a decodable file; metadata is retained in `target/guitar-conservative/dg-capture.json`.

Python regression: 40 poly-directory tests plus 16 frontend configuration tests, 56 passed. Unit-test success does not override the failed strum deployment gate. Production plugin hash is unchanged.
