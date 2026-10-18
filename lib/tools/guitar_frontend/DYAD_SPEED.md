> Retired: real playing failed acceptance on 2026-10-18. Version 0.2.1 removes Dyad and Mode. Historical experiment only.

# Faster dyad experiment, unchanged production mono path

[中文](DYAD_SPEED.cn.md) · [Initial study](DYAD_STUDY.md)

## Scope: 2026-10-18

**Offline only: no dyad CLAP deployment, no Bitwig project or production parameter changes.**
Installed Guitar Frontend and Library hashes are unchanged. The C++ mono engine, plugin.cpp,
and defaults.toml were not modified. This does not promise that future automatic mono/dyad
arbitration can never misclassify arbitrary input.

## Cause and changes

Four slow D/G attacks were primarily blocked by the fundamental-amplitude balance requirement.
Similar plucking force does not imply equal fundamental levels or decay. The speed configuration
reduces the minimum amplitude ratio from 0.55 to 0.20, while retaining 97% harmonic coverage and
two independent partials per note. `dyad_speed.toml` uses a 48 ms frame, 4 ms hop and three-frame
confirmation. Two frames caused mono attack/release false pairs. Shorter 40/32 ms windows failed
real D/G tracking and are rejected.

`dyad_experiment.py` also rejects overtone promotion when a lower observed peak explains it,
and rejects an upper-octave guess when additional partials support a missing lower fundamental.
Such weaker partials can disappear into the allowed 3% residual of a coverage-only test.
A broad resolution-distance veto reduced coverage without eliminating errors and was discarded.
No D/G pitch special cases or release holds hide missed detections.

## Recorded D/G comparison

The first eight requested bursts, 5.40–24.77 seconds of the Spark GO recording:

| Metric | Original 64/8/two frames | Candidate 48/4/three frames |
|---|---:|---:|
| Bursts with some correct output | 8/8 | 8/8 |
| Wrong emitted pairs | 0 | 0 |
| First confirmation | 72–668 ms | **56–90 ms** |
| Correct automatic steady frames | 810/1126 (71.9%) | **2180/2252 (96.8%)** |

Candidate onset estimates: 64, 64, 58, 74, 90, 56, 60, 58 ms. Abstention gaps remain.
This recording is development data, **not independent acceptance data**. Times are relative to
a 10 ms RMS activity threshold, not exact pluck timestamps or end-to-end interface/host/UI latency.
Later uncontrolled audio is excluded. Capture exit code 1 and WAV metadata warnings remain documented.

## Expanded regression

Each group enumerates 1,156 unique cross-string pitch pairs over standard tuning, frets 0–24.
Correct means at least one correct output during the tone and no wrong pair anywhere in the clip,
not continuous tracking accuracy.

| Synthetic input | Correct | Wrong | Abstain | Only after note end |
|---|---:|---:|---:|---:|
| Equal-RMS decaying harmonics | 803 | 0 | 352 | 1 |
| Pure sine pairs | 0 | 0 | 1156 | 0 |
| Perturbed harmonics, ±12 cents, noise, second amplitude 0.85 | 861 | 0 | 295 | 0 |
| Same perturbations, amplitude 0.50 | 791 | 0 | 364 | 1 |
| Same perturbations, amplitude 0.30 | 738 | 0 | 417 | 1 |

The 0.50 group exposed 18 errors before the missing-root protection. These are now development
regressions, not unseen holdouts. Octaves/unisons and uncertain combinations remain conservative;
three notes and strumming are not certified.

Mono protection screening: five phase seeds, **980 full mono attack/release cases and 200
non-overlapping melodies**, no dyad emissions. Historical A3 first 38.2 seconds: 9539 frames,
no dyads. D4 full recording: 11239 frames, no dyads; only 13.9 seconds onward is used as a D4
pitch regression label. **101 pytest tests and 2/2 production detector/CLAP host CTests pass.**
Finite negative results are not universal guarantees.

## Separate mono speed comparison

Rebuilt from current 0.1.2 sources. Short 40/32 ms windows reintroduce low-octave errors in the
D4 recording despite some passing synthetic suites. 64/4/8 fails continuous-melody tests.
64/4/16 passes the existing synthetic suite and selected A3/D4/ringing replay intervals, but
synthetic worst-case attack only improves from 80.25 to 76.24 ms; worst release worsens from
95.15 to 99.16 ms. It needs more independent recordings and is not deployed. Production remains
64/8/24. This is not a claim that mono detection has reached a theoretical limit.

## Reproduction and evidence

```sh
OPENBLAS_NUM_THREADS=1 python -m pytest lib/tools/guitar_frontend -q
OPENBLAS_NUM_THREADS=1 python lib/tools/guitar_frontend/dyad_study.py \
  lib/tools/guitar_frontend/dyad_speed.toml target/dyad-speed-recheck
OPENBLAS_NUM_THREADS=1 python lib/tools/guitar_frontend/dyad_safety_study.py \
  lib/tools/guitar_frontend/dyad_speed.toml target/dyad-safety-recheck
python lib/tools/guitar_frontend/latency_study.py \
  lib/tools/guitar_frontend/latency_study.toml target/mono-timing-recheck
```

Current evidence under `target/guitar-dyad-speed/`: `matrix-lower-root/48ms.json`,
`unequal-0.3.json`, `unequal-0.5.json`, `dg-current.json`, `dg-current-scored.json`,
`a3-current.json`, `d4-current.json`, `mono-phase-safety.json`, `mono-real.json`, and
`mono-timing/all-results.json`. `INVALID-wrong-ringing-source.*` is an invalid early replay
that selected the wrong recording; no conclusions use it. The source hash was corrected and
`mono-real.json` rerun. Earlier files named `matrix-final` or `dg-final` are intermediate results;
use the current/lower-root files listed here.

Next: independent real dyad recordings, then fixed-buffer C++ port and mono/dyad arbitration tests.
Do not delay mono output waiting for dyads, invent second notes on uncertainty, or blindly union
both detectors' outputs. Python is not an audio-callback implementation. Daily use remains the
unchanged mono, display-only guitar path without triggering the synthesizer.
