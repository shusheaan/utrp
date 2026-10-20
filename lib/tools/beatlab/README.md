# Beat Lab — audio to four-category MIDI rhythm

[中文](README.cn.md) · [Validation](VALIDATION.md) · [Clip workflow](WORKFLOW.md)

## One core workflow

**Audio + explicit BPM → automatic analysis → up to A/B/C/D → drum-note mapping and quantization/editing → MIDI clip.**

The primary workflow now records **inside Beat Lab**. One host track receives the microphone and hosts
Beat Lab with monitoring enabled. No separate audio-clip recording or manual WAV export is needed.
Waveform above, four-bar MIDI grid below. MIDI output remains a `.mid` file imported into a drum track;
direct host MIDI clip creation is not implemented.

### Recording

1. Set Bitwig to 4/4, 40–240 BPM; select microphone input and enable monitoring on the hosting track.
2. Host BPM is followed. Select `Once / 4 bars` or `Loop / overwrite`.
3. Press `Record`: four-beat count-in (4, 3, 2, 1), then four bars. No global DAW recording needed.
4. Once finishes automatically; Loop continues until `Stop`. Only the last COMPLETE pass is retained.
   A partial final pass is discarded; stopping before a new full pass retains the earlier take/MIDI.
5. Automatic analysis, mapping and grid editing; export MIDI. Imports/exports are disabled during capture/analysis.
6. Save the Bitwig project: complete source PCM and MIDI analysis are embedded in plugin state, without external WAV files.

The recorder uses a local clock at host BPM, **not DAW transport start/position or arrangement bar alignment**.
Recording can run while transport is stopped if audio callbacks continue. Missing host tempo shows Manual BPM.
Tempo, sample-rate or meter changes abort the unfinished pass rather than silently corrupt timing.
Use headphones: generated clicks are not mixed into captured samples, but speakers can bleed into the microphone.
`Click` controls the recording metronome; count-in always clicks. Hardware round-trip latency has not been calibrated.

**Deployment: 0.3.1 CLAP / Standalone installed and Bitwig reopened. The real user take was restored and reanalyzed: 33 candidates at Gate −45 versus 8 previously, with identical source PCM. Candidate/class accuracy still needs human review; higher counts do not prove correctness. See VALIDATION.**

## Implemented in the local build

- Rust onset detection, spectral features, up to four similar-sound groups, quantization, velocity and MIDI encoding.
  Fewer than four groups are allowed. A/B/C/D is not reliable semantic Kick/Snare/Hat/Clap recognition.
- Record/Stop, Once/Loop, four-beat count-in, waveform and recording cursor. Two buffers retain the last complete pass, not a take history.
- A single WAV drop/import automatically analyzes at the explicit user BPM. New audio must be exactly four bars in 4/4 (16 beats),
  retaining leading silence. Reject tempo/length mismatch without trimming, padding or stretching (one-sample rounding tolerance).
- Four independent note mappings, default 36/38/42/39. GM labels are hints; the downstream kit determines sounds.
- Review is an unconfirmed-event lane, not a fifth sound. It is not exported; reclassify or delete these events.
- Continuous four-bar grid: 1/16, 1/32, 1/64 and 1/16/1/32 triplets; separate bar/beat/subdivision ruler.
- View grid controls display/manual insertion, independently of output Quantize (default Off, preserving microtiming).
- Zoom to four/two/one bars and pan horizontally; lane labels stay fixed. Narrow onset markers and pixel-based hit testing support dense events.
- Edit events, category/velocity, deletion and quantization strength.
- Hear previews the original slice, **not the mapped downstream drum sound**.
- BPM/Gate changes require Reanalyze to avoid silently overwriting edits. A loaded but stale analysis cannot export.
- Export MIDI File is still a development outlet, **not completed MIDI clip integration**.
- Example generates synthetic test input, not evidence of actual beatbox accuracy.

## State and limits

- Pattern v2 has four categories plus Review. v1 remains readable; old Review migrates to Review, never audible D.
- State v3 embeds mono source PCM, capture BPM/rate, pattern, mappings and quantization; legacy pattern-only state remains readable.
  Stop recording before saving to include the latest loop; an ongoing take is not a completed state snapshot.
- New audio: four bars in 4/4, 40–240 BPM, 8–192 kHz, mono/stereo WAV. Legacy 1–8 bar patterns remain readable/exportable.
  WAV sample zero is beat one; recording start is not inferred.
- One source channel at a time. Input L/R selects the recording channel or next WAV import channel. Source WAV is not equivalent to a trimmed/warped clip.
- No semantic model or overlapping-source separation; corrections remain necessary.
- Detection still has a 45 ms minimum onset interval. Finer editable/exportable grids do not establish reliable dense beatbox detection.
- CLAP remains an offline analysis shell: **no live MIDI output, MIDI drag-out or direct host clip writing**.
- Microphone pass-through is always muted; only click and source-slice preview are output. Do not insert into normal instrument, guitar or master chains.

## Build and tests

`engine/`: Rust core; `plugin/`: shell/UI; `tests/`: CLAP/UI tests.
`theme.toml`: independent palette; `dependencies.toml`: pinned dependency archives; `prepare.py`: SHA-256 verification and extraction.

Requires Rust supporting edition 2024, CMake, Ninja, C++17, Python 3.11+, and JUCE Linux development dependencies. Download the four pinned archives as `<name>.tar.gz`, or reuse the existing local download cache:

```sh
python lib/tools/beatlab/prepare.py --downloads target/chordlab-clap-build/downloads --output lib/tools/beatlab/build/deps
cmake -S lib/tools/beatlab -B lib/tools/beatlab/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DBEATLAB_DEPS="$PWD/lib/tools/beatlab/build/deps"
cmake --build lib/tools/beatlab/build -j2
cargo test --offline --manifest-path lib/tools/beatlab/Cargo.toml
cargo clippy --offline --manifest-path lib/tools/beatlab/Cargo.toml --all-targets -- -D warnings
ctest --test-dir lib/tools/beatlab/build --output-on-failure
```

Do not rerun preparation over an existing directory. On a fresh machine first run `cargo fetch --locked --manifest-path lib/tools/beatlab/Cargo.toml`. Rust dependencies are locked. Beat Lab extracts its own sources and does not depend on Chord Lab's patched adapter.

Outputs: `build/BeatLab_artefacts/Release/CLAP/Beat Lab.clap` and `.../Standalone/Beat Lab`.

JUCE 8 requires compliance with its AGPLv3 or commercial license; other dependencies retain their licenses. Commercial distribution has not been reviewed.

## Local deployment / recovery

- Source: `~/work/utrp/lib/tools/beatlab/`.
- CLAP: `~/.clap/Beat Lab.clap`; `.clap` is a directory symlink to `~/storage/daw/UserData/.clap/`.
- Standalone: `~/storage/daw/Tools/BeatLab/Beat Lab`.
- Fixtures: `~/storage/daw/BeatLab/Examples/`.
- Keep user takes/exports under `~/storage/daw/BeatLab/`, outside Git.
- Recreate home links with `lib/tools/daw_backup/live.py` after reinstalling. Close plugin instances, back up old binaries, and copy new builds without replacing the directory symlink.
- `python lib/tools/daw_backup/snapshot.py` saves CLAP and nonignored source in Storage. A snapshot is not a Git commit/push.
