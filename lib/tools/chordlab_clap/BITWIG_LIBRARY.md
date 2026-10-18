# Bitwig Library: 2026-10-17

[中文](BITWIG_LIBRARY.cn.md) · [Initial host validation](BITWIG_RUNTIME.md)

## Project and dependencies

- Project: `~/storage/daw/Library/Library.bwproject`.
- Application menu entry: `Bitwig Library`; native Bitwig Studio 6.1.4 Trial on workspace 2.
- REAPER remains closed. No REAPER project, plugin source, or installed binary changed this session.
- Both hosts share `~/.clap/Chord Lab.clap`, `~/.clap/Guitar Frontend.clap`, and
  `/usr/lib/clap/Surge XT.clap`; no host-specific plugin builds.
- Do not downgrade system GLIBC. Native hosts use the existing system libraries.
  The previous Flatpak runtime provided GLIBC 2.42 while local plugins require 2.43.
  Supporting 2.42 later requires rebuilding relevant plugins against an older sysroot and retesting,
  not replacing the running system's libc.

## Routing

```text
Computer keyboard (editor focused) ─┐
Keystation / All ins ───────────────┴→ Chord Lab → Instrument Selector → Master
                                                   ├─ Warm Veil / Surge XT
                                                   ├─ Dark Choir / Surge XT
                                                   └─ Silver Haze / Surge XT

Spark GO USB mono → Guitar Frontend → Chord Lab → No output
```

- `01 - pad library`: armed, Monitor On, track volume −10 dB. One shared Chord Lab before
  the three mutually selected Pad layers; not three simultaneous instruments.
- `guitar - raw detection`: Monitor On, detector before any DAW effects. Display only;
  it does not drive the Pad. No output avoids doubling Spark's direct monitoring.
  Effects already applied inside Spark cannot be removed by this routing; use a clean setting.
- Guitar detection remains the accepted monophonic version, without polyphony or zero-latency claims.
- The two chains have independent Chord Lab states, not a single global input bus.
- This is a new three-preset research library, not the full 95-preset REAPER migration.

## Operation

1. Select the Pad track. Click a layer's small dot in Instrument Selector to switch sound;
   select its name to inspect that layer and open its Surge XT editor.
2. Computer keys require focus inside Chord Lab and a green Keyboard button.
   `Z/X/C/A/S/D/F`: degrees `6/7/1/2/3/4/5`; `Esc`: move left;
   standalone left `Ctrl` release: move right; `Space`: restore the current chord type's default position;
   `Tab`: cycle triad/seventh/ninth and remember; standalone left `Shift` release: toggle Sustain.
   Modifier combinations suppress standalone Ctrl/Shift actions.
3. Hardware MIDI does not require editor focus, but requires an online controller and enabled track
   input/monitoring. Actual playing and mixed-input acceptance remain pending.
4. Open the guitar track's Chord Lab for pitch display. Detection is enabled/disabled in Guitar Frontend.
5. Adjust overall Pad volume on the track; adjust individual layer volume or Surge Global Volume
   for a single sound. Silver Haze is noticeably quieter; no automatic loudness matching was applied.
6. Save the project for complete plugin state; use Surge Save Patch for standalone presets.
   Three source FXPs are copied into `Presets/`. Surge may display the original load path,
   but all three sounds were verified after moving and reopening the project.

### Preset sources

These reuse the existing A/B/C research patches from `~/storage/daw/patches/pad-lab-20261016/`,
not newly synthesized patches or Bitwig factory presets:

| Patch | Base preset | Character |
| --- | --- | --- |
| Warm Veil | Bluelight / Pads / Juno | Warm, soft analog Pad |
| Dark Choir | Giana Brotherz / Pads / Deep Choir | Dark vocal ambience |
| Silver Haze | Damon Armani / Pads / Freedom Message | Airy, lighter wavetable ambience |

The original `patches.json` records prior parameter edits. Effects are inside the presets;
no additional shared Reverb device was inserted.

## Validation

| Check | Result |
| --- | --- |
| Python regression | 102 passed |
| C++ CTest | Chord 3 passed; Guitar 2 passed |
| Installed CLAP host probes | Ports, state, lifecycle, sample-rate/block-size cases passed |
| Bitwig GUI | 14 keyboard/state checks plus 4 release/focus checks passed |
| Three Pad outputs | Nonzero output, no observed clipping |
| Formal project relocation/save/reopen | All three patches recorded again successfully |
| Real guitar, physical MIDI, mixed input | Final hands-on acceptance pending |
| Full REAPER library, prolonged hotplug, Bitwig MIDI recording | Not certified this session |

Post-reopen recordings targeted Bitwig output ports, not the microphone. Peaks in dBFS:
Warm Veil −16.244449; Dark Choir −18.396375; Silver Haze −33.320721.
These describe the test chord, not a clipping guarantee for arbitrary performances.

Evidence: `target/bitwig-library-validation/`, including logs, JSON, screenshots, WAVs,
and coordinate/window-ID-dependent desktop test helpers. Do not blindly run these helpers on other projects.
`pad-02.wav` is a silent diagnostic take with Keyboard inactive; successful takes are
`pad-02-retest.wav` and `reopened-pad-02.wav`.
Surge logged auxiliary audio-bus activation warnings. Main stereo output was verified;
auxiliary outputs were not, and the logs are not claimed to be warning-free.

## Unresolved hardware blocker

Spark GO disappeared from the system USB/ALSA device list during testing; Keystation remained present.
The setup therefore is not yet certified as immediately playable end to end.

To complete software tests, Bitwig temporarily used the HDMI audio device. Connections to HDMI speakers
were disconnected to prevent unexpected test playback. **This temporary state is not an audible Spark GO setup.**
The project is saved with Warm Veil selected, Sustain Off, and editors side by side.

After Spark GO reconnects:

- [ ] Restore PipeWire / Spark GO / 48 kHz / 256 samples in Bitwig Audio; save/restart if device discovery needs refreshing.
- [ ] Verify stereo Master output to Spark GO and Spark GO mono input on the guitar track, not the computer microphone.
- [ ] Play physical MIDI and monophonic guitar; check sound, gray notes, mixed computer/MIDI input, and releases.
- [ ] Save/reopen and verify actual sound and device recovery before marking full acceptance complete.

## Base content installation (later the same day)

The user requested Essentials/basic content. Essentials v15 was already installed. The remaining
14 packages offered by the current license were installed through the official
Dashboard → Packages → Available → Install All workflow. All 15 entries now show Uninstall
on the Installed page, and the installation manifest contains 15 records.

- Essentials: 298,377,822 download bytes; 343,855,497 content bytes. It contains 2,663 presets,
  126 clips, 270 impulses, 215 wavetables, and 74 curves.
- All currently available content: 7,970,737,978 content bytes (about 7.97 GB).
  New downloads this session: 4,887,752,917 bytes (about 4.89 GB).
  Filesystem `du -sh` reports 7.5G, including allocation differences.
- Added Grand Piano, Electric Keys, Acoustic Drums and Percussion, Classic Drum Machines,
  Bass and Guitar, Polymerics, Drums and Indian Percussion, JoMoX, Raw Cutz, and partner loop packs.
  Several partner packages are explicitly teasers, not full commercial sample libraries.
- Retained `~/.BitwigStudio/installed-packages/5.0/`, automatically indexed by Bitwig.
  Full sample libraries were not copied into the Library project; tracks and audio settings are unchanged.
- Install All covers packages offered by this account/version, not the entire commercial catalog.
  The Essentials content package is distinct from the Bitwig Studio Essentials software edition.
- Evidence: `target/bitwig-content-validation/installed.json` and Packages screenshots.

This content installation does not resolve the Spark GO hardware blocker above.

## Full library migration follow-up

The saved `~/storage/daw/Library/Library.bwproject` now contains 95 original sounds plus three retained pads.
The three-pad project description above is historical; see the [full migration record](../bitwig_library/README.md)
for replacement reverb, shared routing, recording/reopen tests and remaining hardware checks.
Hardware acceptance is still incomplete; do not delete REAPER.
