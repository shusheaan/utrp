# System playback priority

Strict policy: **Spark GO → Woo Audio (existing EQ) → another physical output**.

This is system routing, not plugin DSP. It checks once per second and corrects stored defaults and per-stream targets without restarting Bitwig or the audio server. Device discovery may add its own delay.

## Files and service

- Source: `policy.py`; device names, polling interval and JACK master-port mappings: `policy.toml`.
- Installed unit: `~/.config/systemd/user/utrp-audio-output.service`, enabled at user login.
- The unit runs source from this UTRP checkout. Update `ExecStart` if the checkout moves.
- Status: `systemctl --user status utrp-audio-output.service`.
- Log: `journalctl --user -u utrp-audio-output.service`. Command failures are explicit; systemd retries after two seconds if a device disappears mid-operation.
- Preview only: `python lib/tools/audio_routing/policy.py --dry-run`; empty output means no changes needed.
- Disable: `systemctl --user disable --now utrp-audio-output.service`, then choose a device normally.

## Scope and safeguards

- New applications inherit the default. Existing ordinary PulseAudio and native PipeWire playback streams are redirected too, including explicitly Woo-targeted streams.
- Bitwig and REAPER JACK master outputs `out1/out2` follow the same stereo target.
- Capture, microphone/guitar input, MIDI, recording streams, auxiliary DAW outputs and links to other processing tools remain untouched. No volume, mute, instrument or project changes.
- EQ backend `eq_woo_out` and internal virtual processing streams are excluded to prevent feedback. An orphaned `eq_woo_in` is never selected without the physical Woo output.
- Lower-priority manual device selections are overridden. The Woo branch selects the existing EQ, or raw Woo if EQ is unavailable. Stop the service before intentionally selecting another device or raw Woo.
- Exclusive ALSA applications bypass PipeWire and must be switched to system audio/PipeWire. Additional JACK tools need their stereo master ports listed in TOML.

Uses WirePlumber's supported [default and stream-target routing](https://pipewire.pages.freedesktop.org/wireplumber/policies/linking.html). Raising device priority alone does not override a saved user default; see [Node priorities](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/priorities.html).

## Validation, 2026-10-18

- 20 pytest cases passed: `PYTHONPATH="$PWD" python -m pytest -q lib/tools/audio_routing`.
- Silent Pulse and native PipeWire streams plus the running Bitwig engine passed six live routing scenarios: both devices, Spark output absent, both outputs absent, Woo returning first, Spark returning and taking priority, manual default correction. Each client connected exclusively to the expected sink.
- Output disappearance was simulated by temporary device profiles, not physical USB unplugging or human listening. Original profiles and raw Spark capture → Bitwig in1 were restored.
- The service is enabled and running. Final desktop default and Bitwig master output are Spark GO.
- Initial state, device profiles, graphs and logs: `target/audio-routing/` (runtime evidence, not committed).
