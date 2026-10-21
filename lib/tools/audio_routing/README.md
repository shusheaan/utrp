# Audio routing: Bitwig settings only

[中文](README.cn.md)

## Current state (2026-10-21)

At the user's request, stopped and deleted `utrp-audio-output.service` and `utrp-guitar-input.service`, their login links, repository unit recipes and policy program. No custom output priority or persistent virtual guitar input remains; no replacement service is introduced.

System PipeWire / WirePlumber, existing Woo EQ and plugin-window service are unchanged. Do not reinstall either audio service from older snapshots. The [historical record](HISTORY.md) preserves the old implementation and diagnostics, not current installation instructions.

## Inside Bitwig (pending live setup)

- Connect Spark GO and Woo Audio before opening Bitwig. Use native PipeWire in Settings → Audio and select the required physical devices.
- Choose Woo Audio for output and Spark GO USB mono capture for guitar input, not the removed `Applications → pw-loopback → Spark-GO-Guitar`. Remap all four AG tracks and `GUITAR - raw detection`; keep the raw-detection fader at −∞.
- If Beat Lab microphone input is needed, explicitly map its input bus to SF-558 inside Bitwig. No background program maintains those links; do not enable recording or auto-arm.
- Select input and output independently. No forced switch back to Spark, automatic fallback or seamless hotplug guarantee. Check and reselect disconnected hardware inside Bitwig.

Bitwig was not running and Spark GO was absent from the device graph during removal. No project or preference changes were made; direct hardware input mapping and human listening remain unverified. The saved project may still reference the removed virtual source: service removal does not mean guitar audio is restored.

## Removal verification

Both units report `LoadState=not-found`, `ActiveState=inactive`. The three system audio services remain active; Woo EQ and current playback links are unchanged. Pre-removal backup: `~/storage/daw/Backups/retire-audio-services-20261021T191202Z/`.
