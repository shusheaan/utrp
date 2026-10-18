> Retired: real playing failed acceptance on 2026-10-18. Version 0.2.1 removes Dyad and Mode. Historical experiment only.

# Guitar Frontend 0.2.0 — Mono / experimental Dyad switch

[中文](MODE_SWITCH.cn.md)

## Trying it

Select **GUITAR - raw** in Bitwig and expand the host parameters for **Guitar Frontend**:
- **Detect = On** enables detection; Off releases notes without muting dry audio.
- **Mode = Mono** is the default daily mode: unchanged 0.1.2 algorithm and 64/8/24 ms settings.
- **Mode = Dyad (Experimental)** enables conservative two-note detection. Start with open D/G,
  plucked together at similar strength, muting other strings.
- Return to Mono for single notes. Switching needs no reload; Mode is saved with the project.
- Dyad is NOT automatic mono/poly arbitration. Single notes, octaves and ambiguous signals may stay blank.
- Triads and strumming are unsupported, not guaranteed to be rejected. False detections remain possible.

The plugin uses host-provided parameter UI, not a custom editor.
Mono confidence/stability/release affect Mono only. Gate, input channel and fixed velocity apply to both.
Two read-only MIDI note parameters show both outputs. Pitch evidence means periodicity in Mono
and spectral coverage in Dyad, **not a probability of correctness**.

## Why explicit switching

Automatic arbitration must distinguish harmonics from a genuine second note; concatenating both
detectors is unsafe. Only the selected engine runs. Dyad adds no waiting or FFT work to Mono.
Mode, Detect, input changes and reset clear analysis history and release previously delivered voices.
Rejected events are retried; undelivered note-ons are never counted as delivered.

## Routing and persistence

Dry stereo audio remains sample-exact. Output is MIDI channel 2.
The Library Note Receiver maps 2 to 15; Chord Lab displays channel 15 without forwarding to instruments.
This version changes neither that routing nor guitar detection into synth playback.
Spark hardware effects cannot be undone; keep detection ahead of DAW effects.

CLAP ID remains org.utrp.guitar-frontend. Version 1 states load as Mono.
Version 2 saves Mode; old plugins cannot be assumed to load v2, so rollback needs the pre-upgrade project backup.
Source lives here; ~/.clap/Guitar Frontend.clap is shared by both DAWs, which must reload it.

## Automated evidence, not live certification

- Release and UBSan: 3/3 CTest each, including original mono regressions.
- Python: 108 tests passed.
- Independent CLAP host: original 40 mono rate/block/float32/float64 combinations;
  dyad at five rates in float32/64, mode transitions, partial event rejection, reset,
  stop/start, Detect/input changes, note releases and sample-exact dry audio.
- Parameter boundaries, legacy/new state, partial streams, transactional bad-state rejection and instance isolation.
- Native C++/Python frame parity: target/guitar-dyad-clap/runtime-parity.json.
- Three mono recording replays byte-identical between old/new engines: mono-identical.json.
- Fixed-capacity C++; no Python, file I/O, allocation or locks in the audio callback.

The previous 56–90 ms D/G onset is offline detector timing, excluding interface/host/UI;
see [dyad study](DYAD_SPEED.md). MIDI-keyboard-like latency is not promised.
The live setup is 48 kHz / 256 samples. Higher rates or tiny blocks need separate deadline testing;
offline compute time does not certify zero realtime xruns.

Build/evidence: target/guitar-dyad-clap/.
Previous binary: target/guitar-dyad-clap/Guitar-Frontend-0.1.2.clap.
Refer to this delivery's status for live Bitwig reload and user-play acceptance.

## Deployment status

0.2.0 is installed at the shared CLAP path; running Bitwig has not reloaded it. The on-disk Library project is backed up; saving in-memory edits and reloading awaits confirmation. Native/Python parity: 234 cases, 52148 frames. A3/D4 reference clips emit no dyads. The unlabelled clip is used for parity only, not accuracy claims.

## Bitwig reload verified

Library was saved and normally restarted; the new CLAP is loaded. At 48 kHz / 256 samples, synthetic D3/G3 lit both markers in Dyad and E4 lit its markers in Mono; both cleared on silence. Each six-second master capture had peak=0: no piano retrigger. Test sources are removed and Spark capture_MONO -> Bitwig in1 is restored. Saved in Mono. The bottom-left Guitar Frontend parameter search is filtered to mode; drag Mode up for Dyad, down for Mono. Real-guitar accuracy and perceived latency remain for user testing.
