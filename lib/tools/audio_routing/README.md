# Audio routing: Bitwig settings only

[中文](README.cn.md)

## Current state (2026-10-21)

At the user's request, stopped and deleted `utrp-audio-output.service` and `utrp-guitar-input.service`, their login links, repository unit recipes and policy program. No custom output priority or persistent virtual guitar input remains; no replacement service is introduced.

System PipeWire / WirePlumber, existing Woo EQ and plugin-window service are unchanged. Do not reinstall either audio service from older snapshots. The [historical record](HISTORY.md) preserves the old implementation and diagnostics, not current installation instructions.

## Inside Bitwig (deployed and reopen-verified, 2026-10-21)

- Settings → Audio: native `PipeWire`, Bitwig's Combined Device `Spark GO USB + WooAudio`, with only those two devices enabled and Spark GO as clock master. Manual 128 samples; Automatic sample rate. This is not a system service or a new virtual input program.
- All four AG tracks and `GUITAR - raw detection`: `Spark GO USB → Mono capture_MONO`, replacing the old `Spark-GO-Gtrcapture` / `Spark-GO-Guitar` source. Keep the raw-detection fader at −∞.
- Default Master output: `Spark GO USB → Stereo → Analog Stereo playback_F L/R`.
- To use Woo, select **Master** and change the left Inspector's **output selector** to `WooAudio → Stereo → Analog Stereo playback_F L/R`. Do not replace the entire Audio device group with WooAudio alone, which would remove Spark inputs. This direct Woo path bypasses the existing system Woo EQ.
- Switch back through the same Master output selector. Guitar input, MIDI routing and independent audition groups remain unchanged; no auto-arm is enabled.
- The `beat lab mic` named bus is retained but not remapped or armed in this task; SF-558 is not included in this guitar device group.
- Save Library to retain the selected output. Normal reopen preserved Spark input, Spark Master output and 128 samples. Saving a later manual Woo selection retains that selection; no startup policy forces Spark. Missing-device startup and physical hotplug were not tested; no automatic fallback guarantee.

## Verification and backup

All four AG inputs checked individually, raw detection rechecked. Spark → Bitwig in1 remained connected during the Woo output test; Spark output was then restored. Normal save, exit and reopen verified Master/input/device-group/buffer persistence. Instrument and Audio Auto-arm are off; Beat Lab remained unarmed and recording was not triggered. Human listening remains user acceptance.

Evidence: `target/bitwig-direct-spark/`. Pre-edit project/preferences: `~/storage/daw/Backups/bitwig-direct-spark-20261021T192545Z/`. No controller or plugin source changes. Official mechanism: [Combined Audio Devices](https://www.bitwig.com/userguide/latest/the_dashboard/).

## Removal verification

Both units report `LoadState=not-found`, `ActiveState=inactive`. The three system audio services remain active; Woo EQ and current playback links are unchanged. Pre-removal backup: `~/storage/daw/Backups/retire-audio-services-20261021T191202Z/`.

## 2026-10-23: System In + Out selected the microphone

Spark GO was correctly enumerated by USB/ALSA/PipeWire, but Bitwig Audio was set to `System In + Out` with automatic 256-sample blocks. The live graph connected SF-558 to Bitwig in1 while output still went to Spark. This configuration follows the default system microphone, not the physical guitar input. Available logs do not establish who or what changed the selection.

Restored the existing `Spark GO USB + WooAudio` Combined Device through Bitwig GUI (Spark clock master, manual 128 samples). Woo is absent, but Spark remains usable. Applying settings restores Spark capture_MONO to Bitwig in2 and out1/out2 to Spark stereo. Raw detection retains Mono capture_MONO, Monitor On and −∞; Master shows signal. User confirmed sound returned. No system microphone changes, new services, arming or recording.

Preferences auto-saved at 16:33:21. No restart validation or confirmed project save; this is not a fresh cold-start acceptance. Pre-change backup: `~/storage/daw/Backups/spark-routing-20261023/`; evidence: `target/spark-no-sound-20261023/`. Keep this device group and change only Master output for another speaker; do not select System In + Out to recover output.
