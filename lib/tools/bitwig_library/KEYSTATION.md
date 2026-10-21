# Keystation 61 MK3: Bitwig controls

[中文](KEYSTATION.cn.md) · [Library](README.md)

## Separate inputs

Keep `Generic / Keystation 61 MK3(USB MIDI)` for keys, velocity, pedal, wheels and slider.
The new `UTRP / Keystation Transport` uses only `Keystation 61 MK3(Transport)`, with no Note Input or MIDI output. Buttons never become instrument notes.
`UTRP / Library` retains exclusive audition, editor handling and key synchronization.
Hardware controls do not require Chord Lab focus; computer chord keys still do.

| Hardware | Action |
| --- | --- |
| Play | Start playback from the host playback start; no restart if already playing |
| Stop | Stop and disable Arranger recording |
| Record | Start Arranger recording; press again to punch out while playback continues |
| Up / Down | Previous / next visible GUI track, including folders but skipping collapsed children |
| Left / Right | Collapse / expand the selected folder, or the immediate parent of a leaf; collapsing a parent selects it |
| Center dot | Toggle selected instrument/audio track record Arm; no recording starts; groups and Master are excluded |

Navigation and manual Arm changes are blocked while Arranger recording is enabled. Press Record to punch out (playback continues), or Stop to stop both, before navigating or changing Arm. Press triggers once; release does not trigger; no hold-repeat. Left/right/center no longer seek. Top-level leaf folders never target the project root.
Record is not take deletion or automatic retry. Count-in, loop, punch and capture behavior remain host settings. In Library, select a sound and wait for loading to finish, press Center to arm it, then Record. Selection never auto-arms; selecting another sound in the same group clears that group’s Arm while preserving the other group. There is no need to disable Exclusive audition + editors for this manual Arm workflow. Use a separate project for composition.

## Slider and wheels

- Generic `Cursor Track → Volume CC = 7`, global takeover `Catch`: target the selected track mixer volume, not system/Spark GO volume. Cross the software value before pickup after switching tracks. Check the selected track name, especially for buses/Master, and test the fader without playing first.
- Modulation wheel stays CC1. Its audible effect depends on the patch; assign Surge Modwheel to vibrato or filter cutoff as desired. Sampled piano without such routing may sound unchanged.
- Pitch wheel preserves 14-bit bend; the instrument sets its range. Chord Lab displays Note On pitch, not continuous bent-pitch tracking.
- Octave +/- stays hardware octave control. Advanced remains unchanged. Chord Lab 0.2.11 retains the baseline/pedal behavior.

## Installation and protocol

Copy `Keystation.control.js` and `Keystation.config.js` to `~/Bitwig Studio/Controller Scripts/UTRP/`.
Add `UTRP → Keystation Transport` in Settings → Controllers, assign only Transport input and no output. Never assign Transport as the existing Generic keyboard input.

Real hardware capture on 2026-10-18: channel 1 Note On/Off, Play 94, Stop 93, Record 95, Up 96, Down 97, Left 98, Right 99, Center 100. Hardware already uses Mackie Control.
If switched accidentally, follow the [official guide](https://cdn.inmusicbrands.com/m-audio/maudio_documentation/Keystation%2061%20MKIII%20-%20User%20Guide%20-%20v1.6.pdf): Advanced → DAW, select Mackie Control (green +/- indicators), Enter. Do not factory-reset. Release the pedal during power-up for polarity detection.

## Validation limits

All eight hardware buttons were captured; installed script reports ready without initialization errors.
Original 1.0 Node tests covered mapping, edge gating, both release encodings, invalid messages/channels, signatures/bounds and recording navigation safety; 927 related pytest cases passed then. See current 1.1 validation below.
Installed CLAP probe checks all CC1/7/11 values and representative 14-bit bend values, with sample-exact passthrough on musical channels and reserved-channel isolation; pedal regressions also pass.
User verification of host transport/navigation/fader behavior has been requested. No test take was recorded into the production Library; wheel effects are patch-specific.
Evidence and pre-deployment preferences/project backups: `target/keystation-controls/`. Only the CLAP probe was extended; no plugin rebuild/replacement, system volume or Spark output-policy change.


## Physical reversed-polarity check (2026-10-18)

Captured down=0/up=127 on this unit. Restarting only the keyboard with its pedal connected and released restored down=127/up=0. Startup pedal state determines polarity (official manual linked above); no CC64 reassignment or latch mode is needed. Values alone cannot establish polarity without knowing the physical action. Generic was briefly disabled for capture and restored afterward; Transport and Volume CC=7 were unchanged.

## 2026-10-21: 1.1 folders and manual Arm

- `Keystation.control.js` / `Keystation.config.js`: left/right fold folders, center toggles Arm, up/down follow visible GUI tracks. Play / Stop / Record semantics are unchanged.
- `Library.control.js` is unchanged: independent MIDI/guitar audition, no auto-arm, and a 650 ms post-activation historical Arm cleanup. Wait for sound loading before manual Arm; an early Arm during that settling period can still be cleared by existing cleanup. Ordinary projects remain outside the Library audition policy.
- 405 related pytest cases pass, covering folders/leaves/root/missing selection, audio/MIDI Arm, press gating and recording protection. Live Bitwig console confirms `Keystation Transport 1.1 ready: folders + manual arm`, without initialization errors.
- No test take was created in production Library; physical-button feel and real recording still need user verification. Keys, slider, audio routing and plugins are unchanged.
- Pre-deployment backup: `~/storage/daw/Backups/keystation-fold-arm-20261021T195527Z/`; evidence: `target/keystation-fold-arm/`. No commit/push; finish with a Storage recovery snapshot.
