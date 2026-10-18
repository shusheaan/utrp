# Grid Lab: Warm Fractal Veil

[中文](GRID_LAB.cn.md) · [Library guide](README.md)

## Delivery and provenance — 2026-10-18

- Project: `~/storage/daw/Grid Lab/Grid Lab/Grid Lab.bwproject`.
- Approximately 24 seconds of captured output: `Preview.wav` in that directory.
- Separate learning project; the production Library and CLAP binaries were not changed.
- Host: Bitwig Studio 6.1.4 Trial. Based on the installed Essentials factory preset
  `Poly Grid/Fractal Machine - Divine Radiance.bwpreset`, not an original network built this turn.
- Work completed: preset selection and macro adaptation, sustained chord clip, project configuration,
  save/reopen verification, and output measurement.
- Factory source: `~/.BitwigStudio/installed-packages/5.0/Bitwig/Essentials/Presets/Poly Grid/Fractal Machine - Divine Radiance.bwpreset`.
- Projects, factory content, and recordings remain outside Git; this document records the setup.

## Play

1. Open the project; click `Activate Audio Engine` if shown.
2. In Mix / Clip Launcher, launch the first `S1` clip on `Warm Fractal Veil` using its small triangle.
   Main transport playback alone does not launch a previously stopped Launcher clip.
3. The project runs at 72 BPM, labeled C# Minor. The 16-bar loop holds C#3, E3, G#3, B3
   for 16 bars each at approximately velocity 100: a C#m7 chord, not an automatic chord progression.
4. Select the track, locate Poly Grid in the device panel, and click its colored network thumbnail.
5. Explore `Lowpass → Space → Speed → Steps → Detune`, changing one control at a time.
6. Allow release / space tails after stopping. Do not raise the master abruptly during a quiet passage.
7. Save a copy before rewiring. To play manually, stop the clip, arm the instrument track, and keep
   `All ins`; this example does not include Library's shared Chord Lab routing.

Track gain: -10 dB. Master: -18 dB. Delivery state: stopped, master unmuted.
Default empty Audio 2 and FX 1 tracks remain; neither is required by this sound.

### Macro settings

| Macro | Setting | Purpose |
|---|---:|---|
| Lowpass | 35% | Brightness; raise slightly to inspect harmonics, lower for a darker sound |
| Detune | 15% | Gentle detuning; excessive amounts blur harmony |
| Attack | 85% | Slower onset control |
| Release | 80% | Longer release control |
| Speed | 25% | Internal cycle rate, mapped to discrete multipliers rather than BPM |
| Space | 55% | Factory spatial-mix mapping, not a universal reverb time |
| Steps / Output | Factory values retained | Harmonic-process steps / output gain |

These percentages are normalized macro positions, not Hz, seconds, or detuning cents.

## Why this network merits Grid

Inspected sections include:

- Cycle generator: transport phase, reset, quantization, and rate selection.
- Pitch generator: phase and mathematical transformations generating harmonic-series motion;
  Steps and Step offset control its structure.
- Pulsar synthesis: Phasor, Window, Formant, Blend, phase sync, and sine shaping.
- AR, phase shaping, and Lag for pulse dynamics.
- Voice stacking, detune, and pan for layered stereo motion.
- Average / subtraction for DC removal; Mixer, Audio Out, and scopes for output inspection.

This is fixed harmonic input driving an evolving synthesis structure. It is not guaranteed never
to repeat, and does not add random scale melodies, random chord changes, or a complete arranger.
Harmonic-series motion is not the same as a twelve-tone scale-quantized MIDI melody.
The C# Minor project label does not automatically pitch-correct arbitrary Grid audio.

## Endless reference

The existing `lib/tools/pipeline/specs/endless.toml` suggests bell / FM / warm-pad directions for
the At Your Best outro and ghost / distant-drone directions for Impietas + Deathwish.
This turn did not re-audition or transcribe the album. No claim is made that the original used Grid
or that this example replicates it. Standard warm pads, EPs, and saw chords are usually quicker in
Surge or existing instruments; custom phase, harmonic, pulse-shaping, and modulation relationships
are stronger reasons to use Grid.

## Verification and limits

- Saved, closed, and reopened the project; clip and macro settings persisted and relaunch produced stereo output.
- Piano-roll inspection confirmed the four notes and 16-bar duration.
- Approximately 24 seconds of 48 kHz stereo float output: peak -11.31 dBFS, RMS -36.46 dBFS,
  zero NaNs / Infs, and no samples reaching 0 dBFS. Measurements are not a subjective listening test.
- Speaker links were temporarily disconnected for capture, then restored before delivery.
- No physical MIDI-keyboard, guitar-input, or full-Library regression test was performed this turn.
- Evidence: `target/grid-lab/`. Do not describe this scoped test as full-system acceptance.
- Grid is a Bitwig-native device, not a CLAP transferable to REAPER; render audio for cross-host use.

## Learning sequence and official resources

Start with oscillator → filter → envelope / VCA → output. Then learn LFO, random, and slew;
gate, clock, phase, sequencing, probability, and scale constraints; finally polyphony, voice stacking,
feedback, DC removal, and gain safety. Do not memorize all modules first.

- [The Smallest Generative Patch](https://www.bitwig.com/learnings/1-minute-patch-293/).
- [Modular Concepts & Let's Build an Everything](https://www.bitwig.com/learnings/modular-concepts-lets-build-an-everything-42/): Phase, Pitch, Polyphony, Ambient Set; some sections include downloadable projects.
- [The Grid manual](https://www.bitwig.com/userguide/latest/welcome_to_the_grid/).

Ambient Set is a broader production lesson, not a requirement to build every sound in Grid;
its own downloadable project was not verified.
