# Low-latency two/three-note frontend screening

[中文](README.cn.md) · [Machine-readable results](screening.json)

## Scope and outcome

Target two simultaneous notes first, three experimentally, including ringing arpeggios; no six-string strumming. A phrase can contain arbitrarily many successive pitches, but the first stage tracks at most three simultaneously ringing distinct pitches. Uncertain detections should not emit MIDI. Do not force results into the currently selected chord.

**This iteration screened an open-source candidate; it did not deliver a working polyphonic CLAP. Production Guitar Frontend remains the unchanged monophonic 0.1.0 binary.** Keep audio→MIDI separate from Chord Lab so another detector can replace it without changing the display engine.

## Candidate and experiment

[Polyphonic-Pitch-Detector-for-guitars](https://github.com/luciamarock/Polyphonic-Pitch-Detector-for-guitars), commit `dc4565b3827afd34db47d8ecc770a29b1aed61f0`, upstream GPL-3.0. Sources stay under `target/guitar-poly-research/upstream/`, not integrated into production.

`cPdct::doEnergyAnalysis()` thresholds each semitone resonator at a fixed energy of `0.001`; this output logic does not reject harmonics belonging to other voices or infer independent voices. `WINDOW_SIZE=960` describes analysis updates, not time to a correct complete pitch set. README latency claims are not verification of this revision.

The offline probe compiles only DSP sources, defines `RUN_AT_48KHZ`, and suppresses default real-time logging with `LOG_CONFIG_H`. No algorithm modifications, per-case threshold tuning, GUI, hardware audio or MIDI access.

### Simultaneous attacks: 108 synthetic cases

Peak levels 0.03/0.1/0.3; sine and eight-harmonic decaying signals; octaves, fifths, thirds and adjacent semitones. “Ever exact” means the complete correct set persists for at least 20 ms during the sounding interval. **This is a weak screening condition, not a full-case pass rate.**

| Voices | Cases | Ever exact ≥20 ms | Any spurious pitch |
|---|---:|---:|---:|
| 1 | 36 | 19 | 12 |
| 2 | 48 | 16 | 4 |
| 3 | 24 | 7 | 0 |

Zero spurious pitches in triads does not imply accuracy: missing/no output remains a failure.

Harmonic signals at total peak 0.3: single MIDI 40 emitted 39/40/41/52; dyad 55+59 first became exact after 61 ms; triad 48+52+55 needed 161 ms. Another 18 overlapping-arpeggio cases used 80 ms onset spacing and 400 ms note duration. Mean exact-set time fraction was about 12.72%, including transitions; this is a different metric from “ever exact ≥20 ms.”

These are simplified synthetic screens, not real-guitar accuracy or a verdict on all open-source methods. The unadjusted threshold is input-level sensitive. This revision is unsuitable for production deployment as the requested low-latency polyphonic frontend.

## Alternatives checked on 2026-10-17

- [Jam Origin shop](https://jam.live/shop/): desktop license USD 149.95.
- [Downloads](https://jam.live/downloads/): full-featured trial with interruptions; desktop Windows/macOS, no listed native Linux build. MG3 is beta; MG2 legacy stable. Try before buying.
- [Legacy Linux documentation](https://www.jamorigin.com/docs/daw/) describes Wine/Ardour, not certification of MG3 with this Linux/REAPER/Bitwig setup. Jam Origin was not installed/run this iteration.
- [Basic Pitch](https://github.com/spotify/basic-pitch) is relevant polyphonic transcription research. Its [default model constants](https://github.com/spotify/basic-pitch/blob/main/basic_pitch/constants.py) use an approximately two-second input window. A 256-sample hop is not end-to-end inference latency; it was not wrapped as a live frontend here.

## Required next validation

First resolve two-voice harmonic/octave/fifth ambiguity, level imbalance, repeated picking and overlapping decay, then add three voices. Use labeled clean real guitar, noise and muted/quiet notes; visible activity is not accuracy verification.

Report precision/recall, extra/missing notes, per-note attack P50/P95/max, release delay, missed-detection rate, CPU and dropouts together. Do not omit missed notes to make latency look better. Separate detector delay, USB/host buffers and MIDI→Chord Lab GUI refresh. Direct guitar monitoring is not zero-latency detection. The previous monophonic ~80 ms synthetic attack does not satisfy the new responsiveness requirement.

If the Jam Origin trial runs on Linux, compare identical input. Otherwise do not recommend buying it for Linux first. Its external MIDI output can feed Chord Lab without embedding proprietary code in our CLAP.

## Reproduce

Obtain the pinned upstream revision under `target/guitar-poly-research/upstream/`, preserving its license. From the project root:

```sh
d=$(echo target/guitar-poly-research/upstream/*)
c++ -std=c++17 -O2 -DRUN_AT_48KHZ -DLOG_CONFIG_H \
  -I"$d/pdct_lib/Pdct" -I"$d/pdct_lib/include" -I"$d/pdct_lib/Main" \
  lib/tools/guitar_poly/probe.cpp "$d/pdct_lib/Pdct/cPdct.cpp" \
  "$d/pdct_lib/Pdct/cPdctOutput.cpp" "$d/pdct_lib/Pdct/cComplex.cpp" \
  "$d/pdct_lib/Pdct/cComplexResonator.cpp" -o target/guitar-poly-research/pdct-probe
python lib/tools/guitar_poly/benchmark.py lib/tools/guitar_poly/benchmark.toml \
  target/guitar-poly-research/pdct-probe target/guitar-poly-research/results.json
python -m pytest -q lib/tools/guitar_poly/test_benchmark.py
```

Python requires NumPy, not pandas. Full traces: `target/guitar-poly-research/results.json`. The probe uses native double representation for this Linux x86-64 offline experiment; it is not a distributable plugin.

## Subsequent conservative-output experiment

Production single-note Guitar Frontend subsequently advanced to 0.1.1; the 0.1.0/hash above records the historical screening state, not the current installation. See the [conservative experiment](CONSERVATIVE.md) for offline 1–3-note screening, the D/G control and failed strum rejection. It is not deployed.
