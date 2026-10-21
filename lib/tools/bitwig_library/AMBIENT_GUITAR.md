# Ambient Guitar — four live guitar tones

> Current behavior: controller 0.8 separates MIDI and guitar audition, exclusive within each group but simultaneous across groups. The global 0.6 policy and acceptance below are historical; see [current documentation](README.md).

[中文](AMBIENT_GUITAR.cn.md)

## Project and routing

The project remains `~/storage/daw/Library/Library.bwproject`. **Ambient Guitar** is a new group,
not a separate project or four new detector instances. Existing synth patches, Guitar Frontend,
and Chord Lab engines are unchanged.

```text
Spark GO USB mono input
├─ GUITAR - raw detection
│  └─ Guitar Frontend → existing local Chord Lab; audio fader −∞
│       └─ shared Note Receiver Source FX: channel 2 → 15
│            └─ shared Chord Lab: display only, no synth triggering
└─ selected AG audio track → Chorus / Delay / Hall → Ambient Guitar → Master → Spark GO
```

All four audio tracks use the hardware input directly, not the muted detector track's output.
The new DAW effects cannot feed back into pitch detection. “Raw” means before DAW effects;
it does not guarantee that Spark GO's internal amp/effects are bypassed on USB. Use Spark App
to choose a clean sound and disable internal effects when needed.

## Four starting points

| Track | Effects | Main settings |
|---|---|---|
| AG - 01 Glass Air | Dragonfly Hall Reverb | Clear attack; 22 ms predelay, 3.8 s hall |
| AG - 02 Soft Prism | Surge XT Effects Chorus → Hall | Slow gentle chorus, 5.6 s hall |
| AG - 03 Echo Bloom | Surge XT Effects Delay → Hall | 375 / 500 ms stereo delay, 4.4 s hall |
| AG - 04 Cloud Halo | Chorus → Delay → Hall | 600 / 800 ms stereo delay, 8.2 s hall |

These are already-installed CLAP effects; no purchases, new downloads, or Bitwig-only effects
were needed. Delays use fixed milliseconds, not tempo synchronization. Track faders start at −12 dB
for safe auditioning. [`ambient_guitar.toml`](ambient_guitar.toml) records the complete recipe.
Bitwig saves the actual state; the TOML is documentation, **not an automatic startup override**.
Eight initialization presets are also stored under `~/storage/daw/Library/Presets/Ambient Guitar/`.

## Playing and editing

1. Connect the guitar and Spark GO USB, power it on, expand **Ambient Guitar**, and select an `AG - ...` track.
2. Library controller 0.6 activates, monitors, and arms only the selected sound track, and opens the shared
   Chord Lab. Raw detection stays active. Selecting a synth disables the guitar FX tracks, not detection.
3. In the bottom device panel, change Hall **Late Level** for reverb amount, **Decay** for length,
   and **High Cut** for brightness. Surge **Mix** controls chorus/delay wetness; delay **Feedback** controls
   repeats. Use the track fader for overall level. Increase long tails and feedback cautiously.
4. Plugin windows can be opened manually. The large generic Surge XT Effects editor does not open
   automatically on guitar-track selection; the native Bitwig parameter panel is the default workspace.
5. If hardware direct sound doubles the software tone, lower Spark GO **Guitar Volume**. It controls direct
   monitoring, not computer USB playback. Start at a low listening level.
6. Save with `Ctrl+S`. Exclusive audition cuts the previous track's tail; this is not a seamless live switcher.
   Before multitrack arrangement, disable Controllers → UTRP Library → **Exclusive audition + editors**,
   then manage activation, monitoring, and arm states manually to avoid stacking live inputs.

Guitar note display does not require Chord Lab focus. Computer-keyboard shortcuts still require its
window focused, with A green. Computer chords do not generate guitar audio on these audio-only tracks;
they are effects chains, not MIDI guitar instruments.

## Persistence and validation

- Controller source: `lib/tools/bitwig_library/Library.control.js` and `Library.config.js`;
  deployed under `~/Bitwig Studio/Controller Scripts/UTRP/`.
- Plugins: `/usr/lib/clap/Surge XT Effects.clap` and `/usr/lib/clap/DragonflyHallReverb.clap`.
  REAPER can load the same plugins, but does not automatically inherit Bitwig's tracks or chains.
- Evidence and before/after project snapshots: `target/ambient-guitar/`, excluded from Git.
- Direct script writes exposed a persistence issue: track switching passed while a full restart could still
  restore initial values. The final setup initializes parameters and DSP in a separate CLAP host, saves
  complete presets, then loads those presets into Bitwig. It does not reapply parameters on every startup.
  Acceptance includes closing/reopening, not merely successful write requests.
- Audio checks replay a previously retained Spark GO mono recording, not a new performance or guaranteed
  hardware-effect-free DI. Automated checks do not replace listening, USB latency, or direct-monitor tests.

Hardware reference: [Spark GO USB Audio](https://help.positivegrid.com/hc/en-us/articles/13744445585933-USB-Audio-with-Spark-GO).

## Acceptance results (2026-10-18)

- 14 Python/Node-wrapper tests pass, including guitar/synth exclusivity, retained detection, no automatic guitar FX windows, and recipe-name consistency.
- The final native project was closed/reopened. All eight device identities/counts and all configured parameters passed strict checks; switching to piano and back also passed.
- All eight complete effect states in the final DAWproject export exactly match the initialization presets. The native `.bwproject` is the working project.
- A retained mono guitar recording produced nonzero audio and reverb tails through all four same-parameter chains with Master muted. This audio check preceded final preset import; final import received separate state/reopen checks, not a claimed live listening test.
- Temporary scripts and TCP 19477 were removed. Controller 0.6 is deployed; Master is unmuted, Glass Air is selected, and shared Chord Lab is open. Neither UTRP plugin binary was changed.
- **Spark GO is offline at handoff.** Guitar inputs display `[missing]`; system and Bitwig output correctly fall back to Woo Audio. Reconnect Spark GO and confirm input recovery. If `[missing]` remains, select its mono input in the track Input selector. Hardware end-to-end operation and listening/direct-monitor balance still require the user's check.
- Final evidence under `target/ambient-guitar/`: `acceptance.json`, `reopened-switch-parameters.json`, `export-exact-state-check.json`, `audio-check.json`, `Library-final.bwproject`, and `ready-final.png`. Earlier failed exports/logs are diagnostic history, not final acceptance.


## 2026-10-18: Restore live Spark GO input

This supersedes the earlier missing-input status. Bitwig Audio Selected Device(s) was GB203 HDMI, with no capture ports. An independent output policy routed playback to Spark GO, so audible computer playback did not prove guitar capture was connected. Selecting Spark GO USB restored `capture_MONO → Bitwig in1`; playback currently uses `out3/out4 → Spark GO playback_FL/FR`, at 48 kHz / 256 samples. The block size is not a measured end-to-end latency.

- `GUITAR - raw detection` now has `Mono capture_MONO`, Guitar Frontend `On (mono)`, and its fader remains at −∞ to avoid a duplicate dry signal. Detection precedes all Bitwig guitar effects.
- The shared Chord Lab Note Receiver still sources Guitar Frontend, retaining the existing Source FX / channel 15 display-only route. No per-effect-track detector is required.
- Ready track: `AG - 01 Glass Air`, mono capture, monitor and Arm enabled, −12 dB, routed through Ambient Guitar group to Master. The other three recipes and exclusive selection logic were not changed; all four live hardware chains were not remeasured in this check.
- Turn the physical Spark GO **Guitar Volume** down to zero for software-only monitoring; Bitwig/system controls USB playback level. Do not mute the source inside the Spark App. Spark internal amp/effect processing needs separate verification: pre-Bitwig-effect input is not a guarantee of a true hardware DI.
- Saved `/home/shu/storage/daw/Library/Library.bwproject`. Before/after project, preferences, PipeWire links and screenshots: `target/guitar-routing-restore/`. No plugin binary or controller source changes for this repair.
- Pending user confirmation: audible Bitwig reverb and Chord Lab single-note highlighting with hardware direct monitoring off. Configuration checks are not claimed as live listening acceptance.


## 2026-10-18: Lower monitoring buffer and modest gain

- Library remains an exclusive audition project without new arrangement content. Changed Bitwig Block size from Automatic (actual 256 samples) to manual 128; after restarting the audio engine, `pw-top` confirmed 128 / 48000. Error totals stayed unchanged over roughly nine seconds, not a long-term stability or round-trip latency measurement. Spark hardware format remained 44100 Hz; sample rate was not changed.
- Raised only `AG - 01 Glass Air` from its initial −12 dB to −9 dB. Other AG tracks remain −12 dB; Master remains −1.5 dB. Effects and detection routing are unchanged. Saved the project at 15:53:50.
- 2.67 ms is one block, not total monitoring latency. Playing feel, clipping under hard playing and speaker distortion still require user audition. Revert to 256 and restart the audio engine if persistent crackling occurs.
- Adjust the selected AG track fader gradually while watching track, group and Master peaks. Do not raise raw detection or Spark Guitar Volume to amplify software effects. Evidence: `target/guitar-latency-check/`.


## 2026-10-21: use Bitwig settings

Custom audio services are removed; do not use the old `Spark-GO-Guitar` virtual source. Follow [current routing notes](../audio_routing/README.md) to select physical Spark GO input and the desired output inside Bitwig. Four AG tracks and raw detection still need live remapping after hardware connection. This removal did not edit the project; preserve raw detection at −∞, Keystation, shared detection and independent two-group audition.
