# Initial Bitwig runtime validation (2026-10-17)

[中文](BITWIG_RUNTIME.cn.md)

See [Bitwig Library](BITWIG_LIBRARY.md) for the subsequent formal project and expanded regression.
This page preserves the initial validation record; the Library document describes the current device/project state.

## Environment and project

- Native Linux Bitwig Studio 6.1.4, Trial; REAPER is closed.
- Official `.deb` extracted into `~/opt/bitwig-studio-6.1.4`; application launcher points there.
- Flatpak GLIBC 2.42 could not load local plugins requiring GLIBC 2.43. Switching to the native host resolved this without modifying plugin binaries.
- Saved project: `~/Bitwig Studio/Projects/utrp-lab/utrp-lab.bwproject`.
- Workspace 2; individually hosted plugins; Surge zoom 125%.
- PipeWire / Spark GO USB / 48 kHz / 256 samples; Keystation 61 MK3 USB MIDI controller configured.
- Floating-window rules were installed through Sway IPC for this session, not persisted in desktop configuration.

## Independent chains

1. `keys - chord - surge`: All ins → Chord Lab → Surge XT → Master → Spark GO.
   Armed, track level −10 dB. Computer keys require editor focus and a green Keyboard button. Physical MIDI does not require editor focus.
2. `guitar - raw detection`: Spark GO mono input → Guitar Frontend → Chord Lab.
   Monitor On, No output, avoiding doubled audio alongside Spark direct monitoring. This track is for detection/display only.
   Detection precedes DAW effects but cannot remove effects already applied inside Spark hardware.

This is neither a migration of the 95-patch REAPER library nor a shared-state Chord Lab bus.

## Evidence and limits

- Native scanning/loading succeeded for both custom CLAPs and Surge; two Chord Lab instances coexist.
- With transport stopped, a focused C key produces C/E/G visualization and Surge audio. Explicit Bitwig out1 capture: peak −16.630275 dB, RMS −32.716682 dB.
- A known 293.6647679 Hz D4 signal passed through Bitwig input → Guitar Frontend → Chord Lab and produced a gray D note. The hardware Spark input link was restored afterward.
- Actual PipeWire input and stereo output links target Spark GO, not the computer microphone.
- **Awaiting user performance checks:** physical MIDI sound/display and live guitar recognition in this host.
- **Not fully validated:** every shortcut, mixed-input ownership, save/reopen persistence, prolonged suspension/wake, generated-MIDI recording, and the complete patch library. This is not 100% REAPER/Bitwig equivalence certification.
- Guitar remains the accepted monophonic version; no two/three-note or zero-latency claim.

Local evidence in `target/bitwig-validation/`: `chord-focused.wav`, `chord-focused-held.png`, `d4-sine.wav`, `guitar-d4.png`, `ready.png`.
The earlier `chord-audio.wav` is a silent troubleshooting capture made before keyboard activation, not passing evidence.

## Binary identity

- Chord Lab 0.1.6: `e4d87665e895c035ef726e2d816d0a5c208107d45cb7244e0252aa96a55c1b1b`
- Guitar Frontend 0.1.2: `4ecc3b85f4fc2428741196bfb647cacc5ac4f051e407b3cda5c051c31d902de6`

No plugins were rebuilt and no production REAPER projects were changed.
