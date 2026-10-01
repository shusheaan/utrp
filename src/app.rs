use crate::{
    input::{self, Held, Midi, MidiEvent},
    tui,
};
use anyhow::Result;
use crossterm::event::{self, Event};
use std::time::{Duration, Instant};
use utrp::{
    session::{Action, Session, Target},
    storage::Log,
};

fn guitar_coverage(history: &[Target]) -> (usize, usize) {
    let regions: std::collections::BTreeSet<_> =
        history.iter().map(|target| target.guitar.region).collect();
    let shapes: std::collections::BTreeSet<_> = history
        .iter()
        .filter(|target| target.guitar.task == "chord")
        .filter_map(|target| target.guitar.shape.as_ref())
        .map(|shape| {
            (
                shape.positions.iter().map(|p| p.string).collect::<Vec<_>>(),
                shape.inversion,
            )
        })
        .collect();
    (regions.len(), shapes.len())
}

pub struct App {
    pub session: Session,
    pub instrument: String,
    pub now: u64,
    pub notice: String,
    log: Option<Log>,
    midi: Option<Midi>,
    held: Held,
    midi_fresh_on: bool,
}
impl App {
    pub fn new(session: Session, instrument: String, log: Option<Log>, midi: Option<Midi>) -> Self {
        Self {
            session,
            instrument,
            now: 0,
            notice: "Space = found (self-reported); timeout / D = no credit".into(),
            log,
            midi,
            held: Held::default(),
            midi_fresh_on: false,
        }
    }
    fn act(&mut self, action: Action, id: usize) -> Result<()> {
        let before = self.session.summary(self.now);
        let previous_index = self.session.index;
        if self.session.apply(action, self.now, id) {
            if self.session.index != previous_index || self.session.stopped {
                self.midi_fresh_on = false;
            }
            let after = self.session.summary(self.now);
            self.notice = if after.timed_out > before.timed_out {
                "TIMEOUT: no credit".into()
            } else if after.confirmed > before.confirmed {
                "FOUND: self-reported +1".into()
            } else if after.midi_matched > before.midi_matched {
                "MIDI: exact pitches matched +1".into()
            } else if matches!(action, Action::Faster | Action::Slower) {
                format!(
                    "Next chord: {:.1}s (current deadline unchanged)",
                    self.session.seconds
                )
            } else if matches!(action, Action::Next | Action::Previous) {
                "Navigation: no credit; history does not reroll targets".into()
            } else if matches!(action, Action::ModulateBalanced | Action::ModulateBack) {
                self.session.manual_notice().into()
            } else {
                self.notice.clone()
            };
            if let Some(log) = &mut self.log {
                log.update(&self.session, action, self.now)?;
            }
        }
        Ok(())
    }
    fn keyboard(&mut self, id: usize) -> Result<()> {
        while event::poll(Duration::ZERO)? {
            if let Event::Key(key) = event::read()? {
                if let Some(action) = input::action(key) {
                    self.act(action, id)?;
                }
            }
        }
        Ok(())
    }
    fn midi(&mut self, id: usize) -> Result<()> {
        let events: Vec<MidiEvent> = self
            .midi
            .as_ref()
            .map(|m| m.receiver.try_iter().collect())
            .unwrap_or_default();
        for event in events {
            self.midi_event(event, id)?;
        }
        Ok(())
    }
    fn midi_event(&mut self, event: MidiEvent, id: usize) -> Result<()> {
        self.held.apply(event);
        // Stale batch events still update held notes, but cannot arm a successor.
        if self.session.stopped || self.session.paused || self.session.target().music.id != id {
            return Ok(());
        }
        if matches!(event, MidiEvent::On(..)) {
            self.midi_fresh_on = true;
        }
        // A fresh NoteOn is required on every visit. Once armed, correcting an
        // extra note or releasing sustain may complete the requested chord.
        if self.midi_fresh_on && self.held.matches(&self.session.target().piano_notes) {
            self.act(Action::MidiMatch, id)?;
        }
        Ok(())
    }
    pub fn run(&mut self, terminal: &mut tui::Tui) -> Result<()> {
        let start = Instant::now();
        if let Some(log) = &mut self.log {
            log.update(&self.session, Action::Tick, 0)?;
        }
        while !self.session.stopped {
            self.now = start.elapsed().as_millis() as u64;
            let id = self.session.target().music.id;
            self.keyboard(id)?;
            self.midi(id)?;
            self.act(Action::Tick, id)?;
            terminal.draw(|frame| crate::ui::render(frame, self))?;
            std::thread::sleep(Duration::from_millis(16));
        }
        Ok(())
    }
    pub fn print_summary(&self) {
        let s = self.session.summary(self.now);
        println!("\nU-TR-P | SUMMARY | {}\nScore: {}/100  Found: {}  MIDI matched: {}\nTimeout: {}  Skipped: {}  Unfinished: {}\nPresented: {}  Active time: {:.1}s  Final speed: {:.1}s/chord",
            self.instrument,s.score,s.confirmed,s.midi_matched,s.timed_out,s.skipped,s.stopped,s.presented,s.elapsed_ms as f64/1000.0,self.session.seconds);
        println!("Score = (Space + MIDI matched) / (Space + MIDI matched + timeout + skipped); unfinished excluded.\nSpace confirmations are self-reported, not automatic correctness judgments.");
        println!("Per-key targets (this run; includes skipped/timeouts, not mastery):");
        let counts: Vec<_> = self
            .session
            .key_practice()
            .iter()
            .map(|(key, count)| format!("{key}: {count}"))
            .collect();
        for row in counts.chunks(4) {
            println!("  {}", row.join(" | "));
        }
        let mut keys = std::collections::BTreeSet::new();
        for target in &self.session.history {
            keys.insert(target.music.key.label());
        }
        if self.instrument == "guitar" {
            let (regions, shapes) = guitar_coverage(&self.session.history);
            println!("Presented coverage: {} key/modes, {} regions, {} CHORD string-set/inversion pairs (not mastery)", keys.len(), regions, shapes);
        } else {
            println!(
                "Presented coverage: {} key/modes (piano targets only; not mastery)",
                keys.len()
            );
        }
        if let Some(log) = &self.log {
            println!("Record: {}", log.path.display());
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use utrp::{
        config::{Config, Templates},
        simulator,
    };

    fn app() -> App {
        let config = Config::load(None).unwrap();
        let stream = simulator::stream(&config, Templates::load(None).unwrap(), 42, 48).unwrap();
        App::new(
            Session::new(stream, config.session, 0),
            "piano".into(),
            None,
            None,
        )
    }
    fn play(app: &mut App, id: usize, notes: &[u8]) {
        for note in notes {
            app.midi_event(MidiEvent::On(0, *note), id).unwrap();
        }
    }
    #[test]
    fn summary_coverage_excludes_hidden_detached_grips() {
        let mut config = Config::load(None).unwrap();
        config.guitar.arpeggio_every = 1;
        let mut stream =
            simulator::stream(&config, Templates::load(None).unwrap(), 42, 48).unwrap();
        let mut targets: Vec<_> = (0..100).map(|_| stream.next_target()).collect();
        assert!(targets.iter().any(|target| target.guitar.shape.is_some()));
        assert_eq!(guitar_coverage(&targets), (5, 0));
        targets[0].guitar.task = "chord".into();
        assert_eq!(guitar_coverage(&targets), (5, 1));
    }
    #[test]
    fn midi_correcting_extra_note_matches_current_target() {
        let mut a = app();
        let notes = a.session.target().piano_notes.clone();
        a.midi_event(MidiEvent::On(0, 1), 0).unwrap();
        play(&mut a, 0, &notes);
        assert_eq!(a.session.index, 0);
        a.midi_event(MidiEvent::Off(0, 1), 0).unwrap();
        assert_eq!(a.session.summary(0).midi_matched, 1);
        assert_eq!(a.session.index, 1);
        assert!(!a.midi_fresh_on);
    }
    #[test]
    fn midi_releasing_sustain_can_complete_target() {
        let mut a = app();
        let notes = a.session.target().piano_notes.clone();
        a.midi_event(MidiEvent::On(0, 1), 0).unwrap();
        a.midi_event(MidiEvent::Sustain(0, true), 0).unwrap();
        a.midi_event(MidiEvent::Off(0, 1), 0).unwrap();
        play(&mut a, 0, &notes);
        assert_eq!(a.session.index, 0);
        a.midi_event(MidiEvent::Sustain(0, false), 0).unwrap();
        assert_eq!(a.session.summary(0).midi_matched, 1);
    }
    #[test]
    fn midi_history_navigation_resets_fresh_note_gate_on_every_visit() {
        let mut a = app();
        let notes = a.session.target().piano_notes.clone();
        a.midi_event(MidiEvent::On(0, 1), 0).unwrap();
        play(&mut a, 0, &notes);
        assert!(a.midi_fresh_on);
        a.act(Action::Next, 0).unwrap();
        a.act(Action::Previous, 1).unwrap();
        assert_eq!(a.session.index, 0);
        assert!(!a.midi_fresh_on);
        a.midi_event(MidiEvent::Off(0, 1), 0).unwrap();
        assert!(a.held.matches(&notes));
        assert_eq!(a.session.index, 0);
        assert_eq!(a.session.summary(0).midi_matched, 0);
    }
    #[test]
    fn midi_poll_batch_cannot_credit_or_arm_successor() {
        let mut a = app();
        let notes = a.session.target().piano_notes.clone();
        play(&mut a, 0, &notes);
        assert_eq!(a.session.index, 1);
        a.midi_event(MidiEvent::Reset(0), 0).unwrap();
        let successor = a.session.target().piano_notes.clone();
        play(&mut a, 0, &successor);
        assert_eq!(a.session.index, 1);
        assert!(!a.midi_fresh_on);
        a.midi_event(MidiEvent::Sustain(0, false), 1).unwrap();
        assert_eq!(a.session.index, 1);
        assert_eq!(a.session.summary(0).midi_matched, 1);
        a.midi_event(MidiEvent::On(0, successor[0]), 1).unwrap();
        assert_eq!(a.session.summary(0).midi_matched, 2);
    }
    #[test]
    fn midi_correction_at_deadline_is_timeout_and_paused_notes_do_not_arm() {
        let mut a = app();
        let notes = a.session.target().piano_notes.clone();
        a.act(Action::Pause, 0).unwrap();
        play(&mut a, 0, &notes);
        assert!(!a.midi_fresh_on);
        a.act(Action::Pause, 0).unwrap();
        a.midi_event(MidiEvent::On(0, 1), 0).unwrap();
        a.now = 10000;
        a.midi_event(MidiEvent::Off(0, 1), 0).unwrap();
        assert_eq!(a.session.summary(a.now).timed_out, 1);
        assert_eq!(a.session.summary(a.now).midi_matched, 0);
        assert!(!a.midi_fresh_on);
    }
}
