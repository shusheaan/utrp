# Chord Lab: JSFX → ysfx CLAP prototype

> Historical evidence only: the generic prototype has been removed. These commands are no longer a supported install workflow; use the [current CLAP](README.md).

[中文](PROTOTYPE.cn.md)

## Purpose and scope

Keep native REAPER JSFX as the reference and run the **same unmodified JSFX** inside
CLAP before deciding how to migrate to Bitwig. No chord algorithm was rewritten;
the user's production REAPER configuration, projects, devices and installation are unchanged.

This uses the generic `ysfx-s FX.clap` host. It is **not a self-contained Chord Lab
plugin with a dedicated ID**. The REAPER Lua manager, VKB and window management are not included.

## Measured on 2026-10-17

Linux x86_64, REAPER 7.78, ysfx 0.0.47, Dummy Audio, 48 kHz / 256 samples,
isolated HOME/profile/headless Sway; no real audio or MIDI hardware connected.

| Check | Result |
| --- | --- |
| Ordered MIDI bytes and block-relative sample offsets | 2,376 of 2,377 cases matched; 1 failed |
| 12 keys, 7 degrees, triads/sevenths/ninths, inversions, reset and recall | Listed MIDI cases passed |
| Simulated hardware path: channels 1/15, velocities 1…127 | Passed; not a hardware test |
| Sustain lock, pedal, overlapping degrees, note ownership and panic | Listed MIDI cases passed |
| Actual RPP save/close/reopen | 7 checks passed; ninth/inversion memory retained, Sustain safely reset OFF |
| GUI | Both staff/piano/fretboard groups rendered; mouse Sustain ON → OFF verified |
| Python regression | `70 passed` across prototype and existing Chord Lab tests |

### Known failure: not waived

Case 2368 sends pitch bend, CC1 and Channel Pressure. Native JSFX outputs all three;
CLAP drops `65:d0:45:0`.

The pinned `clap-juce-extensions` dependency at commit
`24e70f7f7cde2842528bb66ff50260b1dc0f4dae` only forwards outgoing messages with
`msg.getRawDataSize() == 3`, excluding two-byte Channel Pressure.
[Adapter source](https://github.com/free-audio/clap-juce-extensions/blob/24e70f7f7cde2842528bb66ff50260b1dc0f4dae/src/wrapper/clap-juce-wrapper.cpp#L1674-L1691).
Program Change, single-byte messages and SysEx also need regression cases; they
were not individually tested. **The upstream binary was not patched or rebuilt.**

### Remaining boundaries

- Initial `TrackFX_SetParamNormalized` writes to Computer mode did not take effect
  after dynamic loading. The fixture enables slider14 via initial plugin state
  for channel 16 command testing. Host automation remains unverified.
- Physical QWERTY/Tab/Enter/semicolon focus handling is not ported. Tests inject
  corresponding channel 16 MIDI commands, not physical keystrokes. REAPER Lua/VKB
  cannot simply run inside Bitwig.
- Forcing an outer-window resize through the window manager clipped contents;
  reopening the editor restored them. DPI and resize behavior need acceptance tests.
- Initial state references an absolute JSFX path; moving folders is not portable.
- Bitwig routing/recording of generated MIDI, transport lifecycle, multiple instances,
  offline rendering, other audio configurations, long-running load, macOS and actual
  synthesizer audio are untested.
- Block-relative offsets do not measure absolute cross-block latency. These checks
  are not a full-equivalence certification.

## Reproduce

Requires Python 3.11+, REAPER Linux and the official ZIP pinned in `prototype.toml`.
The generator verifies SHA-256, retains the release LICENSE, copies unchanged
assets and records their hashes. It does not install, download or launch software.

```sh
curl -fL 'https://github.com/JoepVanlier/ysfx/releases/download/v0.0.47/YSFX.Linux.64-bit.CLAP.zip' \
  -o /tmp/ysfx-0.0.47.zip
python lib/tools/chordlab_clap/prototype.py \
  --archive /tmp/ysfx-0.0.47.zip --output /tmp/chordlab-ab-new
```

The output must not exist. Lua acceptance scripts require `/tmp/chordlab-*`.
In a separate test desktop terminal, use the binary directly, not a personal
launcher that may modify production audio settings:

```sh
ROOT=/tmp/chordlab-ab-new
HOME="$ROOT/home" XDG_CONFIG_HOME="$ROOT/home/.config" \
  /home/shu/opt/REAPER/reaper -newinst -nosplash \
  -cfgfile "$ROOT/reaper/reaper.ini" \
  "$ROOT/prototype.rpp" "$ROOT/reaper/ab_test.lua"
```

Handle normal REAPER prompts and wait several minutes. Inspect `ab-result.txt`
and `ab-events.tsv`; the pinned unmodified wrapper is expected to have the failure
above. Then load/run `reaper/state_ab.lua` through Actions in that **same isolated
instance** and inspect `state-result.txt`. State checks are independent and do not
cancel the MIDI failure. Use a new directory to repeat the complete A/B setup.

```sh
python -m pytest lib/tools/chordlab_clap lib/tools/chordlab/tests -q
luac -p lib/tools/chordlab_clap/ab_test.lua
luac -p lib/tools/chordlab_clap/state_ab.lua
```

Local artifacts are retained in Git-ignored `target/chordlab-clap-prototype/`:
release ZIP, staged binary/source snapshot, per-event logs and screenshots.
Archived RPP paths still reference the original `/tmp` location; this is evidence,
not a relocatable installer. Regenerate initial state for a different directory.

## Recommended Bitwig route

1. **Keep the JSFX engine initially.** Fix/upgrade the adapter and repeat A/B; test
   `Chord Lab → instrument`, generated-note recording, reopening and real keyboards in Bitwig.
2. **Build a dedicated thin wrapper when needed for the complete workflow.** Reuse
   JSFX while adding input/focus handling, explicit parameters, bundled resources
   and stable plugin identity. Keep one chord implementation across both hosts.
3. **Rewrite natively only for demonstrated engine limitations**, such as UI or
   real-time requirements that cannot reasonably be met, or required note-expression
   semantics beyond the existing MIDI model. Retain JSFX as the reference.

Do not maintain two independent chord algorithms prematurely, or treat this generic
host prototype as a finished migration.

## Upstream and distribution

[ysfx upstream](https://github.com/JoepVanlier/ysfx) supplies the JSFX host. The
prerelease binary ZIP contains an AGPLv3 LICENSE, retained unchanged. The library
repository's Apache label is not a blanket license for the plugin binary. Review
all dependencies/assets before redistribution. This experiment is local only;
no plugin was published and no fork/branch was created.
