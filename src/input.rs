use anyhow::{Context, Result};
use crossterm::event::{KeyCode, KeyEvent, KeyEventKind, KeyModifiers};
use midir::{MidiInput, MidiInputConnection};
use std::{
    collections::BTreeSet,
    io::{self, Write},
    sync::mpsc::{self, Receiver},
};
use utrp::session::Action;

pub fn action(key: KeyEvent) -> Option<Action> {
    if key.kind != KeyEventKind::Press {
        return None;
    }
    if key.code == KeyCode::Char('c') && key.modifiers.contains(KeyModifiers::CONTROL) {
        return Some(Action::Stop);
    }
    match key.code {
        KeyCode::Enter => Some(Action::Stop),
        KeyCode::Char('e' | 'E') => Some(Action::ModulateBalanced),
        KeyCode::Char('q' | 'Q') => Some(Action::ModulateBack),
        KeyCode::Char(' ') => Some(Action::Confirm),
        KeyCode::Char('w' | 'W') => Some(Action::Faster),
        KeyCode::Char('s' | 'S') => Some(Action::Slower),
        KeyCode::Char('a' | 'A') => Some(Action::Previous),
        KeyCode::Char('d' | 'D') => Some(Action::Next),
        KeyCode::Char('p' | 'P') => Some(Action::Pause),
        KeyCode::Tab | KeyCode::Char('m' | 'M') => Some(Action::ToggleAuto),
        _ => None,
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MidiEvent {
    On(u8, u8),
    Off(u8, u8),
    Sustain(u8, bool),
    Reset(u8),
}
pub fn parse_midi(message: &[u8]) -> Option<MidiEvent> {
    if message.len() != 3 || message[1] > 127 || message[2] > 127 {
        return None;
    }
    let channel = message[0] & 15;
    match message[0] & 0xf0 {
        0x90 if message[2] > 0 => Some(MidiEvent::On(channel, message[1])),
        0x80 | 0x90 => Some(MidiEvent::Off(channel, message[1])),
        0xb0 if message[1] == 64 => Some(MidiEvent::Sustain(channel, message[2] >= 64)),
        0xb0 if matches!(message[1], 120 | 123) => Some(MidiEvent::Reset(channel)),
        _ => None,
    }
}
#[derive(Default)]
pub struct Held {
    pressed: BTreeSet<(u8, u8)>,
    sounding: BTreeSet<(u8, u8)>,
    sustain: BTreeSet<u8>,
}
impl Held {
    pub fn apply(&mut self, event: MidiEvent) {
        match event {
            MidiEvent::On(c, n) => {
                self.pressed.insert((c, n));
                self.sounding.insert((c, n));
            }
            MidiEvent::Off(c, n) => {
                self.pressed.remove(&(c, n));
                if !self.sustain.contains(&c) {
                    self.sounding.remove(&(c, n));
                }
            }
            MidiEvent::Sustain(c, true) => {
                self.sustain.insert(c);
            }
            MidiEvent::Sustain(c, false) => {
                self.sustain.remove(&c);
                self.sounding
                    .retain(|p| p.0 != c || self.pressed.contains(p));
            }
            MidiEvent::Reset(c) => {
                self.pressed.retain(|p| p.0 != c);
                self.sounding.retain(|p| p.0 != c);
                self.sustain.remove(&c);
            }
        }
    }
    pub fn matches(&self, notes: &[u8]) -> bool {
        self.sounding.iter().map(|p| p.1).collect::<BTreeSet<_>>()
            == notes.iter().copied().collect()
    }
}
pub struct Midi {
    pub receiver: Receiver<MidiEvent>,
    _connection: MidiInputConnection<()>,
}
impl Midi {
    pub fn connect() -> Result<Self> {
        let input = MidiInput::new("utrp piano")
            .context("MIDI unavailable; guitar mode does not require MIDI")?;
        let ports = input.ports();
        anyhow::ensure!(!ports.is_empty(), "no MIDI inputs available for piano");
        for (i, port) in ports.iter().enumerate() {
            println!("{i}: {}", input.port_name(port)?);
        }
        print!("MIDI input number: ");
        io::stdout().flush()?;
        let mut line = String::new();
        anyhow::ensure!(io::stdin().read_line(&mut line)? > 0, "input closed");
        let index: usize = line.trim().parse().context("expected MIDI port number")?;
        let port = ports.get(index).context("MIDI port index out of range")?;
        let (sender, receiver) = mpsc::channel();
        let connection = input
            .connect(
                port,
                "utrp piano input",
                move |_, bytes, _| {
                    if let Some(event) = parse_midi(bytes) {
                        let _ = sender.send(event);
                    }
                },
                (),
            )
            .map_err(|e| anyhow::anyhow!("connect MIDI: {e}"))?;
        Ok(Self {
            receiver,
            _connection: connection,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn controls_and_repeat() {
        for (key, expected) in [
            ('w', Action::Faster),
            ('s', Action::Slower),
            ('a', Action::Previous),
            ('d', Action::Next),
            (' ', Action::Confirm),
            ('e', Action::ModulateBalanced),
            ('q', Action::ModulateBack),
            ('E', Action::ModulateBalanced),
            ('Q', Action::ModulateBack),
        ] {
            assert_eq!(
                action(KeyEvent::new(KeyCode::Char(key), KeyModifiers::NONE)),
                Some(expected)
            );
            for kind in [KeyEventKind::Repeat, KeyEventKind::Release] {
                assert_eq!(
                    action(KeyEvent::new_with_kind(
                        KeyCode::Char(key),
                        KeyModifiers::NONE,
                        kind
                    )),
                    None
                );
            }
        }
        assert_eq!(
            action(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE)),
            Some(Action::Stop)
        );
    }
    #[test]
    fn tab_toggles_timer_only_on_press() {
        for (kind, expected) in [
            (KeyEventKind::Press, Some(Action::ToggleAuto)),
            (KeyEventKind::Repeat, None),
            (KeyEventKind::Release, None),
        ] {
            assert_eq!(
                action(KeyEvent::new_with_kind(
                    KeyCode::Tab,
                    KeyModifiers::NONE,
                    kind
                )),
                expected
            );
        }
    }
    #[test]
    fn control_c_still_stops() {
        assert_eq!(
            action(KeyEvent::new(KeyCode::Char('c'), KeyModifiers::CONTROL)),
            Some(Action::Stop)
        );
    }
    #[test]
    fn midi_boundaries_and_noteoff() {
        for bytes in [
            vec![],
            vec![0x90],
            vec![0x90, 60],
            vec![0xf8],
            vec![0x90, 128, 90],
        ] {
            assert_eq!(parse_midi(&bytes), None);
        }
        assert_eq!(parse_midi(&[0x92, 60, 90]), Some(MidiEvent::On(2, 60)));
        assert_eq!(parse_midi(&[0x92, 60, 0]), Some(MidiEvent::Off(2, 60)));
        let mut held = Held::default();
        held.apply(MidiEvent::On(0, 0));
        assert!(held.matches(&[0]));
        held.apply(MidiEvent::Off(0, 0));
        assert!(held.matches(&[]));
    }
    #[test]
    fn sustain_and_inversion_matching() {
        let mut h = Held::default();
        for n in [60, 64, 67] {
            h.apply(MidiEvent::On(0, n));
        }
        assert!(h.matches(&[60, 64, 67]));
        assert!(!h.matches(&[64, 67, 72]));
        h.apply(MidiEvent::Sustain(0, true));
        h.apply(MidiEvent::Off(0, 60));
        assert!(h.matches(&[60, 64, 67]));
        h.apply(MidiEvent::Sustain(0, false));
        assert!(h.matches(&[64, 67]));
        h.apply(MidiEvent::Reset(0));
        assert!(h.matches(&[]));
    }
}
