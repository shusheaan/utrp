# Fixed audio routing: playback priority and guitar input

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
- Only the dedicated virtual guitar input backend is managed. Other capture streams, the default microphone, MIDI, auxiliary DAW outputs and other processing tools remain untouched. No volume, mute, instrument or project changes.
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

## Persistent guitar input (2026-10-19)

The single supported setup uses **native Bitwig PipeWire**, not JACK. Select `System Out` and manual **128 samples** in Audio.
The four Library AG tracks and `GUITAR - raw detection` select
`Applications → pw-loopback → Spark-GO-Guitar → capture_MONO`.

Signal path: `Spark GO capture_MONO → Spark-GO-Internal-Capture → Spark-GO-Guitar → Bitwig`.
`pw-loopback` is PipeWire's audio bridge. These two names are the capture and source ends of one process, not duplicate solutions.
Choose only `Spark-GO-Guitar`, never the Internal-Capture monitor port.
See the official [Loopback module](https://docs.pipewire.org/page_module_loopback.html).

Reason: starting Bitwig without Spark reproduced an HDMI selection with no input ports even after Spark returned.
The persistent source remains available; the policy reconnects its backend by device name rather than transient node IDs.
Missing Spark means silence, **never a microphone fallback**. SF-558 remains the default voice source.
The policy checks every second after device discovery; reconnection is not instantaneous.

### Installation and recovery

Install both `.service` files from this directory into `~/.config/systemd/user/`, retaining the repository paths for `policy.py` and `policy.toml`:

```sh
systemctl --user daemon-reload
systemctl --user enable --now utrp-guitar-input.service utrp-audio-output.service
systemctl --user status utrp-guitar-input.service utrp-audio-output.service
python lib/tools/audio_routing/policy.py --dry-run
```

`utrp-guitar-input.service` creates one mono bridge; `utrp-audio-output.service` maintains existing playback priority and that bridge's backend.
Fully reopen Bitwig after initial deployment or source recreation to refresh its Applications enumeration.
No temporary null source, JACK rule or experimental route is deployed. Disable both services to disable the complete policy.

Daily sequence: **power on Spark GO and Keystation, connect USB and allow system discovery → start Bitwig → open Library → select a track and play**.
MIDI still uses the existing Keystation controller and shared Chord Lab. The Library exclusive-audition controller is unchanged and does not apply to ordinary projects.
Disconnected/unrecognized hardware, stopped services or muted volume cannot be solved by a routing guarantee; normal use requires no repeated Input selection.
This change does not adjust faders, effects or Spark hardware direct monitoring.

### Verification

- 66 routing, backup and Library-controller regression tests passed. Normal exit, source recreation and Bitwig reopen restored the saved input and retained 128 samples.
- Spark profile disappearance/return kept the virtual source connected to Bitwig, never fell back to a microphone and automatically restored Spark. Not physical unplugging or a system reboot.
- SF-558 microphone, Keystation controller and exclusive audition are retained. Physical guitar/keyboard listening awaits user confirmation.
- Runtime evidence: `target/input-autoconnect/`; recovery manifest includes the new service.

## Beat Lab microphone input (2026-10-20)

`microphone_inputs` in `policy.toml` connects the specific SF-558 USB microphone's `capture_MONO` to Bitwig's named `beat lab mic` L/R ports. Only these named ports are managed; the `in3` guitar input and other projects' Arm/Monitor states are untouched. Missing hardware never falls back to guitar or another microphone. Recreated ports reconnect by name. Bitwig keeps WooAudio playback; the recording track selects `beat lab mic` with Arm and Auto Monitor. Update the explicit configuration when changing microphones.

Validation: `python -m pytest lib/tools/audio_routing -q` passed 38 tests. Disconnecting the live right input was automatically repaired; the plugin showed nonzero input. Real beatbox capture/accuracy remains untested.
