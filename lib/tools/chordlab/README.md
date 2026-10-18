# Chord Lab embedded engine

[中文](README.cn.md) · [Current CLAP product](../chordlab_clap/README.md)

This directory is the **current CLAP's musical and drawing engine source**, not an
installable REAPER JSFX product. The legacy Lua/VKB launcher, key map and installer
have been removed at the user's request. Do not install this directory into REAPER Effects.

Keep the eight EEL/JSFX files, notation image/license and theme configuration: the current
CLAP embeds these assets. `generate_theme.py` validates `theme.toml` and regenerates
`theme.jsfx-inc`; its historical header is retained for byte-identical embedded assets.
Rebuild CLAP after changing runtime assets. The current computer key map is
`../chordlab_clap/keyboard-map.txt`.

`tests/` contains theme validation and musical-engine reference fixtures. A native JSFX
instance may be staged in an isolated scratch host solely as a regression reference;
this is not a supported second product or a daily-use workflow.

```sh
python -m pytest lib/tools/chordlab/tests lib/tools/chordlab_clap lib/tools/library -q
```

`guitar.toml` / `generate_guitar.py` compile a conservative guitar catalog; audio processing only performs lookups.
[Modes and controls](../chordlab_clap/GUITAR_VOICING.md).
