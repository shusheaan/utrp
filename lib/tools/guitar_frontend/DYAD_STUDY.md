> Retired: real playing failed acceptance on 2026-10-18. Version 0.2.1 removes Dyad and Mode. Historical experiment only.

# Conservative dyad study: production mono remains unchanged

[中文](DYAD_STUDY.cn.md)

## Scope

2026-10-18: retain the working monophonic experience and investigate approximately equal-strength guitar dyads across the fretboard; no triad implementation yet.
This pass implements an **offline two-pitch hypothesis engine and replay harness**, not a deployed polyphonic CLAP.
No Guitar Frontend installation, Library edit, mono parameter change or display-only routing change is performed.
Synthetic success does not establish real-guitar accuracy, live latency or complete fretboard support.

## Implementation

- `dyad_experiment.py` uses causal Hann-window spectral peaks, interpolation, fundamental balance, frequency separation, harmonic coverage and ambiguity rejection.
  Each proposed note additionally needs two partials independently supported outside the other note's harmonic series.
- A single harmonic-series explanation takes precedence, including missing-root ambiguity. Two strong peaks alone are not evidence of two strings.
- Two consecutive agreeing frames are required; uncertainty immediately withdraws the dyad hypothesis. No release hold disguises uncertainty.
- Future integration needs explicit mono/dyad arbitration; combining contradictory independent detectors is not sufficient.
- Pure sine dyads without independent overtones, many octave/fifth pairs and unresolved low close intervals intentionally abstain.
  Real guitar with weak fundamentals or nearly sinusoidal timbre may also be missed. Abstention is not correct recognition.
- `dyad_experiment.toml` covers standard tuning, frets 0–24, E2–E6 (MIDI 40–88), with 48/64 ms windows and an 8 ms hop.
  Production mono remains MIDI 38–88.
- Python/NumPy/SciPy allocate memory: **this code must not run inside a CLAP audio callback**. It is an algorithm feasibility study before fixed-buffer C++ work.

## Reproduction

```sh
python -m pytest lib/tools/guitar_frontend -q
OPENBLAS_NUM_THREADS=1 python lib/tools/guitar_frontend/dyad_study.py \
  lib/tools/guitar_frontend/dyad_experiment.toml target/guitar-dyad-study
python lib/tools/guitar_frontend/dyad_replay.py \
  lib/tools/guitar_frontend/dyad_experiment.toml INPUT.wav START_SECONDS END_SECONDS OUTPUT.json
```

- `dyad_study.py` enumerates different-string fret combinations from 0–24: **1,156 distinct-pitch pairs**.
  Awkward stretches are included as pitch-range stress tests, not recommended fingerings. Unison strings collapse to one MIDI pitch and are excluded.
- Equal-RMS sine and harmonic signals are tested separately, with 80 ms silence, 160 ms sound and 80 ms silence.
  Full onset/release traces are checked: any wrong emitted pair makes the whole case wrong, even if correct frames also occur.
- A perturbed set changes phase and harmonic decay, detunes notes by opposite ±12 cents, scales the second note to 0.85 amplitude and adds noise.
  These remain synthetic checks, not an independent real-guitar validation set.
- Controls include strong-overtone and missing-fundamental single notes, silence, DC, noise, nonfinite input, clipping and a few unsupported triads.
  A third tone hidden among another tone's harmonics can still yield a two-note subset; universal triad rejection is not guaranteed.
- The previously user-confirmed first 38.2 seconds of the A3 recording screen for mono-to-dyad false output. Its uncontrolled ending is excluded.
  SciPy's non-audio WAV metadata warning remains visible in the replay log.

## Initial failure and correction

Peak balance, harmonic coverage and two-frame agreement alone produced **17 wrong cases** in the 48 ms full-trace matrix, despite no errors in the initial two-complete-frame-only check.
Nearby frequencies shift apparent spectral peaks during attacks/releases. Requiring independently supported partials addresses this failure class; merely increasing strength or confidence does not.
Pre-correction evidence is retained in `target/guitar-dyad-study/before-partial-check/`. This is a development regression, not proof of universal correctness.

## Next real-guitar step

Record D3 + G3 (open strings 4 and 3) at approximately equal strength, mute other strings, avoid strumming, and repeat with silence between attacks.
Then test higher positions, thirds/fifths/octaves and unison controls. Do not deploy to daily Library before labeled real dyad recordings are evaluated.
Raw-input requirements remain: a sufficiently clean Spark preset, no DAW effects before analysis, and eventual detection used only for Chord Lab display.

## Results and deployment decision

The corrected full-onset/release run uses 1,156 pairs per row. Correct means at least one confirmed correct dyad during the 160 ms sound and no wrong pitch pair anywhere; **it is not continuous tracking accuracy**. Late-only detections occur after the sound ends and do not count as successful attacks.

| Signal | Window | Correct observed | Wrong | Entirely abstained | Late only |
|---|---:|---:|---:|---:|---:|
| Equal-RMS harmonic | 48 ms | 817 | 0 | 329 | 10 |
| Equal-RMS harmonic | 64 ms | 851 | 0 | 293 | 12 |
| Perturbed set | 48 ms | 860 | 0 | 292 | 4 |
| Perturbed set | 64 ms | 918 | 0 | 230 | 8 |

An additional 1,156 pure-sine pairs per window all abstain: an explicit cost of independent-partial evidence. Real guitar with weak overtones can also be rejected.
Synthetic D3+G3 first confirms at about **56 ms** in both configurations. This observation-window delay excludes interface/host/display and Python execution time, and is not a live latency guarantee.
The historical A3 replay emits no dyads in 4,770 frames at 48 ms and 4,768 at 64 ms. One 64 ms triad control emits a two-note subset of the actual notes; universal triad/strum rejection is not established.

85 Guitar Frontend pytest cases, 647 project-related pytest cases, and the original two mono CTest suites pass. Passing regression tests does not establish sufficient algorithm coverage.
Production `Guitar Frontend.clap` and `Library.bwproject` SHA-256 values are unchanged. Evidence is in `target/guitar-dyad-study/`;
final machine-readable results are `summary.json` and `48ms.json` / `64ms.json`. Logs retain pre-correction scoring; late-only cases were separated from abstention without changing detector output.

**Decision: retain the offline experiment; do not deploy it as the daily CLAP.** Labeled real-dyad recording awaits user readiness. Mono remains available; desktop and audio routing are untouched.

## 2026-10-18: first Spark GO open D/G recording

Evidence is in `target/guitar-dg-validation/`: `dg-open-01.wav`, `routing-01.txt`,
`analysis-01.json`, and `analysis-01.log`. An additional recording branch used Spark GO capture,
not the computer microphone; existing Bitwig routing was unchanged. The WAV decodes to 60 seconds
of 48 kHz mono float32 audio, with a −17.06 dBFS peak and no clipped or non-finite samples.
`pw-record` exited with code 1 and an empty log; the cause remains unresolved, so this is not a
clean capture-process exit. The SciPy non-audio chunk warning is retained. Dropouts and end-to-end
latency have not been measured.

Eight automatically segmented bursts at 5.40–24.77 seconds contain approximately 147/196 Hz
fundamentals and corresponding harmonics, consistent with the requested D3/G3. Later audio after
approximately 36 seconds contains other pitches and has no confirmed performance labels; it is
excluded from D/G acceptance scoring. No detector settings were tuned to this recording.

| Window | Bursts with at least one correct pair | Wrong pair frames in these bursts | Correct steady frames / all steady frames | First confirmation range |
|---|---:|---:|---:|---:|
| 48 ms | 8/8 | 0 | 807/1126 (71.7%) | 64–676 ms |
| 64 ms | 8/8 | 0 | 810/1126 (71.9%) | 72–668 ms |

Steady windows exclude each burst's first 150 ms and last 100 ms; they are not manually verified
frame-level ground truth. Confirmation time is relative to a 10 ms RMS activity threshold, not an
exact pluck timestamp, and excludes interface/host/UI latency. Both variants confirm four bursts
quickly but take roughly 0.49–0.68 seconds for the other four, with subsequent abstention gaps.
**Real D/G detection is feasible, but fast and stable tracking has not passed acceptance.**
Eight bursts with some correct output does not mean 100% real-time accuracy. The production mono
plugin and Library remain unchanged; the dyad experiment is not deployed.

## Follow-up

Initial results remain historical; see [dyad speed](DYAD_SPEED.md) for subsequent changes, failed candidates and deployment limits.
