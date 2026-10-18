# 0.1.1 UI calibration and Core audition project

[中文](UI_CALIBRATION.cn.md)

## Fix

The pinned ysfx Linux SWELL interpreted positive font heights as em heights,
producing larger text than current REAPER native JSFX. The wrapper `font_source()`
backports [current SWELL line-metrics sizing](https://github.com/justinfrankel/WDL/blob/main/WDL/swell/swell-gdi-lice.cpp).
JSFX music logic, font settings, palette and clef assets are unchanged. CLAP adds
its own 40 px keyboard toolbar; whole-window pixel identity is not intended.

Native JSFX and CLAP were compared side by side at equal gfx dimensions on the
real desktop. Key labels, chord buttons and instrument markers now match in size;
the original colors remain. Surge Royal stays at 125% without arbitrary stretching.

## Local audition project

`/home/shu/storage/daw/Core.RPP` has one track:
`Keystation USB MIDI → Input FX: Chord Lab CLAP → FX: Surge XT instrument → Master`.
There is no Shared MIDI input, old JSFX or Lua/VKB routing. The old `synth.rpp`
is unchanged. Recording is armed, monitoring enabled, track gain -6 dB.
The current output goes through the existing EQ to WooAudio, not the disconnected
Spark GO. Click CLAP content for Keyboard ACTIVE before computer-key playing.
Physical MIDI does not need editor focus. A stopped-transport D-key test produced
a track peak of approximately 0.122. Human physical-key acceptance remains pending;
connected ports alone do not prove physical key delivery.

## Regression evidence

`ui_acceptance.json` identifies the new binary; local evidence is under
`target/chordlab-clap-0.1.1/evidence/`: 82 pytest, 2 CTest, CLAP ABI probe,
2379 MIDI A/B, 7 save/reload checks and 22 parameter checks passed.
`acceptance.json` and `mixed_acceptance.json` remain historical 0.1.0 evidence;
not all historical GUI/mixed-input checks were rerun for this binary.
Bitwig has not been tested in a real host session.
