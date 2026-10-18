# Chord Lab mixed input and daily workflow

[中文](MIXED_INPUT.cn.md) · [Main guide](README.md)

## Recommended REAPER routing

`Keystation USB MIDI → track Input FX: Chord Lab CLAP → regular FX: Surge/piano → reverb`

The editor feeds computer-key commands directly into the same engine. REAPER VKB is
not needed. Disable the legacy Lua/VKB keyboard capture and do not chain the original
JSFX and CLAP together. The production synth.rpp now uses one shared CLAP input track;
see the [library guide](../library/CLAP_MIGRATION.md).

1. Enable the Keystation **USB MIDI**, not Transport, input in Preferences / Audio / MIDI
   Devices. Playing notes does not require enabling them as action/control messages.
2. Select that device as the track MIDI input, All channels. Hardware channels 1–15
   are supported; channel 16 is reserved for Chord Lab commands. Normally use channel 1.
3. Arm the target track and enable input monitoring. Avoid multiple monitored instruments.
4. Put one Chord Lab in Input FX; keep the instrument and audio effects in regular FX.
5. Enable the green **Keyboard** button and click inside the editor, then play computer chords and hardware together.
6. Start recording with the DAW's mouse button, refocus the editor, and play. Enabled, focused capture consumes
   unmodified Space; it cannot simultaneously act as the DAW play shortcut. Release computer
   keys before switching windows to stop recording.
7. Save the project. Routing persists, but the input device, arm and monitoring must remain valid.

Input FX is optional, not an always-running system service. Regular FX before the instrument
also supports live playing. Actual recording was tested: Input FX writes generated chords
and external notes to the MIDI item. Ordinary Record input does not automatically capture
regular-FX output; that placement needs an appropriate output-recording route.

Existing timeline items do not pass through Input FX. Its diagram should not be expected to
follow every recorded-item playback. Use regular-FX placement for playback visualization;
do not blindly insert two control instances in series. Recording and playback visualization
are separate routing requirements.

## Focus and display

- **Green Keyboard + editor focused:** computer commands and hardware input both work.
- **Another window focused (Keyboard turns red):** new computer keys are not captured; generated held
  notes are released. Hardware continues if the track remains processing/monitored.
- **Red Keyboard:** computer capture is disabled, not MIDI processing or plugin bypass.
- **Editor closed:** computer holds and Sustain lock are cleared; the processor stays in
  the chain and hardware can continue, without a visible diagram.
- Track monitoring off / bypass / offline is not equivalent to hiding the editor.

Hardware playing does not require editor focus; computer chords do. Holding a computer
chord while clicking Surge releases that chord under the current safety policy. Sustain
may retain sound but is not a dedicated chord latch. Host-global/system shortcuts can
still take precedence. There is no cross-window keyboard hook.

Gray means **outside the displayed scale/chord**, not simply “from hardware.” In C major
with CM7 selected below:

| Hardware note | Upper scale diagram | Lower chord diagram |
| --- | --- | --- |
| C/E/G/B | Colored active scale tone | Colored active chord tone |
| D | Colored active scale tone | Gray |
| F sharp | Gray | Gray |

Staff, piano and fretboard share these rules. External gray notes disappear on release;
member notes return to their pale reference color. The view tracks MIDI holds, not sounding
sustain/reverb tails, and does not automatically recognize/select a new chord from input.
Visible ranges are limited: the piano covers MIDI 38–86 (D2–D6); staff and fretboard have
separate limits. MIDI can still sound outside the visible range.

## Shared pitches and sustain

Computer and hardware share ownership of identical pitches on channel 1. Each new
attack retriggers via Note Off → Note On, with the physical key's exact velocity.
Releasing one owner preserves the other; only the last release sends the final Note Off.
Other channels remain independent.

S shows the **pedal-up baseline**, toggled by Space or clicking S:

| S | Pedal up | Pedal down |
| --- | --- | --- |
| Red | Sustain off | Sustain on |
| Green | Sustain on | Sustain off |

Pedal events never change S. Each musical channel tracks its own CC64 state, with
64 as the on threshold. This is binary sustain, not continuous half-pedaling.
It never mutes notes whose keys are still held. Reversed physical pedal polarity
must be calibrated on the pedal/keyboard; a CC64 value alone cannot reveal foot position.
Existing focus/close cleanup resets the computer baseline to red, without losing
physical pedal state. Plugin reload clears transient pedal state; release and press again.

## Additional acceptance

Historical musical-engine acceptance (before the 0.1.2 UI-only update):
- `mixed_ab.lua`: 42/42 Track FX and 42/42 Input FX; both implementations compared with
  independently specified MIDI expectations, including offsets.
- Channels 1/2/15, scale/non-scale notes, both shared-pitch release orders, velocity and pedal lock.
- `mixed_record.lua`: each Input FX version recorded six notes with exact pitch/channel/velocity
  and positive lengths, not channel-16 command notes.
- Actual editor screenshots manually checked for matching gray/colored mixed-note behavior.
- Keystation 61 MK3 detected; isolated REAPER opened `/dev/snd/midiC4D0`. Physical playing
  still requires observed user-generated events; synthetic tests do not certify the hardware.

See `mixed_acceptance.json` and local `target/chordlab-clap-release/evidence/mixed/`.
Reproduce by staging `/tmp/chordlab-mixed-track` and `/tmp/chordlab-mixed-input`, running
`mixed_ab.lua` in each empty isolated project, then `mixed_record.lua` in the Input FX profile.
If REAPER prompts to save recordings, choose Save All, only in the scratch project.
