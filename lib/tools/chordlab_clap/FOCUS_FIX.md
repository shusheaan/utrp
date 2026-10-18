# Keyboard focus synchronization — 0.1.4

[中文](FOCUS_FIX.cn.md)

## Cause and behavior

The button displayed only the capture-enabled preference. Green now requires enabled
capture, a visible editor, JUCE component focus, and native peer focus. The peer check
protects against stale component focus in embedded hosts. Key input, release polling,
and the indicator share this predicate.

- Focus loss turns the button red and releases computer-held keys; it does not reset
  Sustain or the enabled preference.
- Clicking back restores green unless manually disabled or disabled with Esc.
- Clicking a focus-inactive red button activates capture. Its displayed state is sampled
  on mouse-down so focus changes during a long click cannot invert the intended action.
- Hardware MIDI processing is independent. No musical core, routing, parameter or state
  format changes were made.

## Verification

[Machine record](focus_acceptance.json); local backups/evidence:
`target/chordlab-focus-0.1.4/evidence/`.

- 113 pytest tests, 2 CTest tests, and the CLAP ABI/MIDI/state/lifecycle probe passed.
- 14 rendered-color and keyboard-state checks passed in isolated REAPER, including
  held-key focus loss, refocus, persistent manual disable, long activation clicks and Esc.
- Harness correction: XTest clicks reached host controls without changing Sway seat/X11
  focus. Initial failures were not valid focus-loss cases. Explicit native focus changes
  were used for the passing rerun.
- Production REAPER: switching from Chord Lab to sfizz turned Keyboard red; returning
  turned it green. Computer-key piano output peaked at `0.3699069917202`.
- With user approval, backed up, saved, restarted REAPER and loaded 0.1.4. Preserved all
  102 tracks, 93 Surge engine/wavetable states, 2 sfizz states, effects and gains, and the
  single shared CLAP. Restored pre-test chord memory and parameters, except the existing safe-load Sustain
  reset from ON to OFF. State bytes match apart from that parameter; saved the project.

This does not certify physical MIDI hardware, Bitwig, or every platform. Sustain remains
an independent control.
