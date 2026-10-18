# Bitwig portability assessment (2026-10-17)

[中文](BITWIG_ASSESSMENT.cn.md)

> See [runtime validation](BITWIG_RUNTIME.md) for subsequent host testing. The earlier
> static assessment below retains historical installation, key-map, and binary details.

## Decision and scope

Try the existing Linux x86_64 `Chord Lab.clap` in Bitwig first. Do not rewrite the
musical engine or create a separate host-specific product. This is a source and
documentation review, not a Bitwig certification. No Bitwig executable was found
in PATH or common `/opt`/Flatpak locations. No installation, plugin changes, or
production project edits were performed.
Reviewed binary SHA-256:
`a17a614adaebb33fb31b346d51afca49610e75203a23d27151be448acec41c44`.

Bitwig supports CLAP devices in device chains and offers isolated plugin processes.
[Devices](https://www.bitwig.com/userguide/latest/vst_plug-ins/),
[hosting modes](https://www.bitwig.com/userguide/latest/vst_plug-in_handling_and_options/).

## Architecture and reusable scope

`lib/tools/chordlab/` holds EEL harmony, MIDI, memory and notation/UI code. These
assets are embedded, executed by ysfx inside the plugin, and wrapped by the JUCE
editor/control layer plus clap-juce-extensions in `lib/tools/chordlab_clap/`.
`CMakeLists.txt:19–49` declares a MIDI effect with ID `org.utrp.chordlab`;
the binary has one MIDI input/output, no audio ports, and 18 parameters.

`embedded_source.cpp` extracts assets into an instance-private temporary directory.
`port_upstream.py` removes the original machine's script path from state and loads
the embedded engine. A writable temporary directory, system libraries, and X11/
XWayland remain required. The plugin does not need REAPER, its Lua scripts, or VKB.

Chords, inversions, triad/seventh/ninth selection, seven-degree memory, notation,
piano/fretboard visualization, mixed input and buttons can reuse the implementation.
`Library mode.lua:25–68` separately manages REAPER sends, solo, instrument unloading
and editor windows. That workflow and `synth.rpp` are not portable plugin features.

## First test and remaining work

Start with an empty Bitwig project and `Chord Lab → Surge XT → effects → Master`,
not the complete 95-patch library. Later, a shared control track can feed instruments.
Bitwig's Note Receiver imports project note signals, but receiving within a device
chain is not proof that the resulting notes are recorded at the track input. Verify
the actual recording source/tap and inspect the resulting note clip.
[Routing](https://www.bitwig.com/userguide/latest/routing/),
[recording](https://www.bitwig.com/userguide/latest/recording_clips/).

Required checks:

- Scanning/category, zero-audio MIDI chain, downstream audio, actual hardware input.
- Focused computer keys, Tab/Enter/semicolon, mouse, long holds, focus loss and close.
  System/global shortcuts cannot be unconditionally overridden by a plugin.
- Processing while stopped/idle: the GUI queue drains in process callbacks; no
  explicit keyboard wake request was found. The adapter returns CONTINUE, but host
  suspension still needs testing. Start diagnostics with Suspend=Never if necessary,
  then test the default. Bitwig documents Never/When silent/Trust plug-in modes.
  [Suspend](https://www.bitwig.com/userguide/latest/the_unified_modulation_system/).
- MIDI 1.0 channels 1–15, velocity and overlapping ownership; channel 16 currently
  carries internal control. Do not force MPE.
- Independent instances, bypass, suspend/resume, transport/loop, save/reopen.
- State restoration exists, but there is no generic preset import/export UI.
  Separate hosts do not automatically synchronize memory or exchange project files.
- Musical automation must be distinguished from internal command/status parameters.
- The current ELF references GLIBC_2.43. Test a native same-machine installation
  first; older distributions/Flatpak runtimes may need a compatible rebuild.
  macOS/Windows require platform-specific builds, not this Linux binary.

## Evolution without a fork

The embedded EEL engine is not inherently a temporary dead end. Retain it until a
concrete event-model/performance requirement justifies migrating a component.

Important existing constraints:

1. `chordlab.jsfx:68–69` and `midi.jsfx-inc:93` deliberately lock key changes during
   held notes and playback/recording. Live modulation/transposition requires defined
   timing and release/Sustain semantics; changing DAWs does not unlock it.
2. A sequencer should schedule against host musical time in the processing engine,
   not a GUI timer. Loop/seek/offline rendering are new work, despite existing host
   time translation into ysfx.
3. CLAP packaging does not provide native note expression or polyphonic modulation
   automatically. Full MPE conflicts with the reserved control channel; separate
   internal commands from external MIDI when that requirement becomes concrete.
4. Preserve plugin ID and existing parameter IDs/meanings. New parameters require
   updating the fixed-18 adapter. Version and migrate stored state; test old projects.
   Keep one musical implementation and host-specific workflow templates only.

## Library migration is separate

The actual project contains 93 Surge CLAP instances, two sfizz LV2 instances and a
ReaVerbate folder effect. Surge/Chord Lab are the first portable candidates. Bitwig
lists VST2.4/VST3/CLAP formats; do not assume existing LV2 instances load unchanged.
sfizz upstream offers VST3, allowing the original SFZ to be loaded again with settings
and sound verification. ReaVerbate being labeled VST in RPP does not establish that
the REAPER-bundled binary is a portable standalone plugin.
[Bitwig formats](https://www.bitwig.com/modern-foundations/),
[sfizz upstream](https://github.com/sfztools/sfizz-ui).

## Conditional effort estimates

Assumes an available Bitwig installation, native Linux on this machine, physical
test access, and no major host/runtime defect. These are engineering estimates,
not a background-job ETA or a compatibility guarantee.

| Deliverable | Estimate |
|---|---|
| Scan existing binary, GUI, first computer/hardware notes into Surge | 0.5–2 hours |
| Current feature parity, recording template, limited fixes and two-host regression | Approximately 1–3 workdays total |
| Generic harmony-memory import/export, if needed | Additional 0.5–1 workday |
| Full library, sfizz format replacement, effects and selection workflow | Additional 2–5 workdays; exact window automation requires separate scoping |
| New transposition/arrangement/sequencer, MPE, other operating systems | Separate requirements, not included |

Order: establish real hardware input → one-track Bitwig smoke test → dual-host
feature/recording acceptance → library/template → new musical features. The current
physical MIDI incident has not passed a human retest; changing hosts or passing
synthetic MIDI tests must not conceal that unresolved input path.

## Release gates

Use the same source/binary hash and record host versions/settings. Compare identical
deterministic MIDI pitch/channel/velocity/order/timing and ownership behavior. Test
real computer/hardware/mixed input and gray-note visualization; stopped/playing/
recording/loop/idle wake; focus/close/bypass/multiple instances; recorded generated
notes without regeneration; save/reopen, old-state migration and safe Sustain reset.
REAPER must not regress, and Bitwig acceptance remains pending until actually tested.
