# Chord Lab 0.1.9: left-hand controls

[中文](LEFT_HAND.cn.md) · [Usage](README.md)

| Key | Action |
| --- | --- |
| Z / X | Degree 6 / 7 |
| C | Degree 1 |
| A / S | Degree 2 / 3 |
| D / F | Degree 4 / 5 |
| V / G | Move voicing down-left / up-right while holding a chord |
| Space | Toggle Sustain on press; holding/releasing does not retoggle |
| Tab | Cycle triad / seventh / ninth, with immediate recall memory |

The first row of twelve tonality shortcuts and the mouse Sustain button are unchanged.
Old Esc/Ctrl/H/J/K/L/semicolon/Enter actions are removed. This consolidates chord, movement,
and sustain controls, not tonality selection.

Computer commands require **green Keyboard and editor focus**. Space works alongside held chord keys.
Shift and Ctrl have no standalone actions; modifier combinations do not execute commands.
Genuine focus loss or disabling Keyboard safely releases generated notes.

Space toggles Sustain, not DAW transport. System/host-global shortcuts can still take priority.
Hardware MIDI routing and velocity remain unchanged and do not require editor focus.

## Implementation

- `keyboard-map.txt` generates the CLAP-only `keyboard_map.h`; the retired JSFX/VKB
  key map no longer configures the current product.
- Space uses the ordinary ordered key stream; standalone modifier actions have been removed.
  Linux `PhysicalKeys` observes only its own X11 editor peer, never global shortcuts.
- Ordinary key-release sweeps always consult physical X11 state. A missed JUCE key-up
  cannot leave a chord held indefinitely, including while the editor remains focused.
- Musical algorithms, MIDI semantics, parameters, stable CLAP ID and shared input topology
  are unchanged. JSFX is a musical A/B baseline, not a second maintained product.

## Historical 0.1.5 acceptance scope

See [this release's results](left_hand_acceptance.json). Complete local artifacts are under
`target/chordlab-full-0.1.5/`. GUI checks use an isolated REAPER, headless Sway/XWayland
and XTest. `evidence/test_keys.py` records the exact run; its scratch paths, window IDs and
coordinates must be adapted to a new test instance, never blindly run on production.

Automated tests do not certify physical finger playing, Bitwig, macOS/Windows, native Wayland
plugin editors or every host-global shortcut configuration. Native left/right modifier handling
currently targets Linux X11/XWayland only.

The project and old plugin are backed up before restarting to load the new binary. Musical
memory is preserved; Sustain resets OFF on reload by the existing safety policy. Library
checks temporarily silence the master, then restore gain and selection and remove the test FX.

## 0.1.8: held-chord navigation and click focus

Hold C (or Z/X/A/S/D/F), tap G to move up-right or V to move down-left.
The chord keeps sounding; each real press moves once and OS repeat is ignored.
Esc and Ctrl no longer move voicing. Standalone left Shift release still toggles
Sustain; Space and Tab are unchanged.

With user approval this machine now uses Sway `focus_follows_mouse no`: hovering
another window does not change focus; clicks and focus shortcuts still do.
This is a desktop-wide policy, not plugin focus stealing. Genuine focus loss still
turns Keyboard red and safely releases computer notes.
See [G/V and focus acceptance](GV_FOCUS.md).

## 0.1.9: Space toggles Sustain

Each real Space press toggles Sustain, including alongside held chord keys. Holding and releasing
Space do not toggle again. Standalone Shift and the former Space reset shortcut are removed.
G/V, Tab, the Sustain button, click-focus policy and hardware MIDI routing are unchanged.
The 0.1.8 and earlier acceptance sections above describe historical versions only.
