# Beat Lab: clip-first workflow

[中文](WORKFLOW.cn.md)

## Current direction: in-plugin recording (later confirmation, 2026-10-20)

The user now chooses recording inside the plugin; direct clip drag no longer blocks the prototype.
One host microphone track → Beat Lab Record / four-beat count-in → four-bar Once or Loop overwrite → Stop / automatic analysis → MIDI file.
Waveform above, MIDI grid below; host BPM with local capture clock; completed source PCM embedded in project plugin state.

- [x] Capture, last-complete-loop retention, partial-pass discard and tempo/rate/meter boundary protection.
- [x] Automatic analysis, waveform and source state persistence without manual WAV saving.
- [x] Synthetic end-to-end tests: stopped host transport, input R, host BPM, MIDI events and state recovery.
- [ ] Verify live Bitwig microphone routing, audible count-in and latency; real beatbox accuracy remains separate acceptance.
- [ ] Direct MIDI clip output and reusable cross-recording Sound Set templates remain pending.

The following is the historical clip-first plan, not a prerequisite for the current recording entry point.

User-directed revision, 2026-10-20. **Next-iteration design, not implemented functionality.**

## Intended workflow

1. Record normally on any Bitwig audio track at the project tempo, trim and select an audio clip.
2. Transfer the project clip into Beat Lab; test direct drag-in first. No manual save/find-WAV step.
3. Display source, BPM, duration and waveform; edit onsets, up to four A/B/C/D groups, Review, quantization and velocity.
4. Map each class to a MIDI note. The destination Drum Machine or other instrument supplies the sounds.
5. Return a standard MIDI clip to an instrument track; test drag-out first, assess direct insertion separately.

No fixed input/drums track names or second recording pass. Beat Lab is a conversion
editor, not another recorder or a drum library. Record/count-in/Save Take/Import WAV
is no longer the intended primary workflow. Software-managed intermediate files are
acceptable; user-managed file round-trips are not.

## Findings and limitations

- The user deleted both experimental tracks from Library. Their absence was visually
  confirmed and the project saved. Do not recreate them. Keep the source and analysis engine.
- Local Bitwig 6.1.4 `Clip`, `CursorClip`, `ClipLauncherSlot` and `ClipLauncherSlotBank`
  interfaces expose note editing/empty clip creation; no selected audio clip PCM/source-file
  access was found in these interfaces. This is not a claim about all uninspected interfaces.
- [Official Sampler documentation](https://www.bitwig.com/sampler/) describes clip
  drag-in for a built-in device, not proof of equivalent third-party CLAP support.
- [Stable CLAP extensions](https://github.com/free-audio/clap/tree/main/include/clap/ext)
  provide no generic project clip read/write protocol. Tempo, MIDI output ports and
  arranger clip insertion are separate capabilities.
- **Actual third-party drag payloads have not been tested.** JUCE file-drop support
  alone would not establish compatibility. Handle or explicitly reject private objects/`.bwclip`.
- A source WAV alone does not establish clip trim offsets, start, looping, stretch or
  multiple audio events. Never silently analyze the entire source instead of the selection.
  Do not default to parsing private `.bwproject` files.

## Next implementation and acceptance steps

- [ ] Test audio clip drag payloads in an isolated project.
- [ ] Verify trim, leading silence, stretch, looping and multiple audio events; preserve beat one and selection range.
- [ ] Verify MIDI drag-in to an instrument track for timing, length, velocity and mapping.
- [ ] Choose direct drag/drop or a host bridge from evidence; report limitations before adding workaround UI.
- [ ] Reuse the Rust engine and grid; preview mapped notes through the destination instrument.
- [ ] Persist audio references/copies and analysis state; editor close/project reopen must preserve editing and playback.
- [ ] Verify source preservation, destination isolation and Undo/redo boundaries.
- [ ] Validate actual user beatboxing, not only synthetic demos.

The initial design pass saved the cleaned Library without binary changes.
The subsequent local implementation is recorded below.

## Four-category simplification — 2026-10-20

Local sources now remove capture and Record/Stop/Save Take, adding automatic WAV analysis, four mappings and v1 Review compatibility.
Review is not a fifth sound. Output remains a development MIDI file; both clip endpoints remain pending and the new binary is not deployed.

## Dense four-bar grid — 2026-10-20

- [x] Exactly four bars for new audio, tempo/length validation without silent trimming/stretching.
- [x] Continuous four-bar display, subdivision/beat/bar ruler, 1/16, 1/32, 1/64 and triplets.
- [x] Independent View grid/Quantize, default Off; four/two/one-bar zoom and horizontal panning.
- [x] Individual hit testing of 256 markers and coordinate roundtrips without changing pattern data.
- [ ] Cross-take Sound Set: persist sound templates and note mappings instead of regrouping every take.

Local build only, not deployed. Project clip integration remains pending. Dense display does not validate dense onset detection.

### Too few detected hits (v0.3.1)

Keep the waveform; no new take is needed. Lower `Gate dB` (more negative, e.g. −36 → −42 → −45), then click `Reanalyze`. This reuses original PCM and retains mapping/quantize controls, but replaces manually edited events; back up the project first if those edits matter. Gate persists in project state. Raise it if noise becomes false hits. Turning up the track fader does not repair already captured audio.
