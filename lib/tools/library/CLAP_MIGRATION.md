# Library: single-product CLAP migration

[中文](CLAP_MIGRATION.cn.md)

## Daily use

Open `~/storage/daw/synth.rpp`; `Start library.lua` remains the startup action.
The sole input track, **CHORD LAB CLAP - shared MIDI input**, hosts
`org.utrp.chordlab` in Input FX. Configure the physical MIDI device there.
Selecting a sound switches MIDI sends, solo, instrument online/offline state and
editors, without cloning Chord Lab. All 95 sounds share musical state; only one
instrument is auditioned at a time.

Click CLAP content for **Keyboard** green + editor focused before using computer keys. Z/X/C/A/S/D/F, Tab,
Esc, standalone left Ctrl/Shift releases and Space belong to CLAP; see [current controls](../chordlab_clap/README.md); the old global Tab script is retired.
Physical MIDI channels 1–15 preserve velocity and do not require editor focus.
Channel 16 remains reserved for control. Closing the editor does not stop physical
MIDI. The old VKB and `Chord Lab mode.lua` no longer start. The updated
`Open Chord Lab.lua` only shows an existing CLAP and never inserts JSFX.
After editing a synth, click Chord Lab again before computer-key playing.

Use Master for overall gain and each sound's fader for its gain. Existing sounds,
gains and Basic Keys reverb are preserved. Do not add parallel monitoring of the
same device on instrument tracks. This is an exclusive audition library, not a
multitrack production template: recording currently targets the sole armed shared
input; independent multitrack recording requires separate routing design.

## One product

Future behavior development targets CLAP only, without mandatory native-JSFX
feature parity. EEL music/UI sources remain in `../chordlab/` and are embedded at
build time; rebuild and deploy `.clap` after editing them. Legacy Lua/VKB flows,
A/B records and rollback projects remain historical, not active products.
Library Lua is only the REAPER routing/editor adapter, not a keyboard/chord engine.

## Migration and safety

The original project, REAPER configuration and old scripts are backed up under
`~/storage/daw/Backups/synth-pre-clap-*`. `migrate_state.py` imports v2 seven-degree
memory once, rejecting ambiguous/invalid sources. It preserves key, degree, chord
type, inversion, register, velocity and Enabled, while clearing transient held
notes, commands and Sustain. Host normalized parameters and serialized memory are
checked before removing JSFX. REAPER CLAP parameters use normalized ranges;
legacy JSFX integer commands cannot be copied directly into those host calls.
All 93 Surge editor-only zoom factors are set to 125%, without changing engine XML or wavetables.
The temporary `Core.RPP` is deleted after acceptance; `synth.rpp` stays canonical.

## Acceptance

`clap_audit.lua` silences Master and temporarily injects test MIDI, not a legacy
Chord Lab instance. It visits every sound, measures chord-protocol and ordinary
MIDI audio, and checks one online instrument, solo, armed source and instrument
window, with VKB closed. Exit removes the fixture and restores Chord Lab state,
Master gain and selection. Do not switch projects or save during the audit.
This is not physical-key or subjective-timbre certification; focused computer keys
also need real GUI-event testing. Evidence is under `target/synth-clap-migration/`;
`VALIDATION.md` is historical.
