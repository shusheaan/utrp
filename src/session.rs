use crate::{
    config::Timing,
    guitar::{GuitarPlanner, GuitarTarget},
    progression::{ChordEvent, ManualModulation, Progression},
};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Target {
    pub music: ChordEvent,
    pub guitar: GuitarTarget,
    pub piano_notes: Vec<u8>,
}

pub struct PracticeStream {
    engine: Progression,
    guitar: GuitarPlanner,
    base: u8,
}
impl PracticeStream {
    pub fn new(engine: Progression, guitar: GuitarPlanner, base: u8) -> Self {
        Self {
            engine,
            guitar,
            base,
        }
    }
    pub fn next_target(&mut self) -> Target {
        let music = self.engine.next_event();
        let guitar = self.guitar.target(&music);
        let inversion = music.id % music.chord.tones.len();
        let piano_notes = music.chord.piano_notes(inversion, self.base);
        Target {
            music,
            guitar,
            piano_notes,
        }
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Action {
    Confirm,
    MidiMatch,
    Previous,
    Next,
    Faster,
    Slower,
    Pause,
    ToggleAuto,
    ModulateBalanced,
    ModulateBack,
    Stop,
    Tick,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Outcome {
    Confirmed,
    MidiMatched,
    TimedOut,
    Skipped,
    Stopped,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Attempt {
    pub outcome: Outcome,
    pub elapsed_ms: u64,
    pub limit_ms: Option<u64>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Summary {
    pub presented: usize,
    pub confirmed: usize,
    pub midi_matched: usize,
    pub timed_out: usize,
    pub skipped: usize,
    pub stopped: usize,
    pub score: u32,
    pub elapsed_ms: u64,
}

pub struct Session {
    stream: PracticeStream,
    pub history: Vec<Target>,
    pub attempts: Vec<Option<Attempt>>,
    pub index: usize,
    pub seconds: f64,
    pub automatic: bool,
    pub paused: bool,
    pub stopped: bool,
    timing: Timing,
    started: u64,
    deadline: Option<u64>,
    remaining: u64,
    paused_at: u64,
    paused_ms: u64,
    turn_started: u64,
    turn_pause: u64,
    pub turn_limit: Option<u64>,
}
impl Session {
    pub fn new(mut stream: PracticeStream, timing: Timing, now: u64) -> Self {
        let target = stream.next_target();
        let limit = (timing.seconds_per_chord * 1000.0).round() as u64;
        Self {
            stream,
            history: vec![target],
            attempts: vec![None],
            index: 0,
            seconds: timing.seconds_per_chord,
            automatic: timing.automatic,
            paused: false,
            stopped: false,
            started: now,
            deadline: timing.automatic.then_some(now + limit),
            remaining: limit,
            paused_at: 0,
            paused_ms: 0,
            turn_started: now,
            turn_pause: 0,
            turn_limit: timing.automatic.then_some(limit),
            timing,
        }
    }
    pub fn target(&self) -> &Target {
        &self.history[self.index]
    }
    pub fn manual_notice(&self) -> &str {
        self.stream.engine.manual_notice()
    }
    pub fn pending_manual_label(&self) -> Option<String> {
        self.stream.engine.pending_manual_label()
    }
    pub fn key_practice(&self) -> &std::collections::BTreeMap<String, usize> {
        self.stream.engine.key_practice()
    }
    /// Preview the current phrase, including its unplayed music, without
    /// generating guitar targets or adding unpresented items to the score.
    pub fn phrase_events(&self) -> Vec<&ChordEvent> {
        let phrase = self.target().music.phrase;
        self.history
            .iter()
            .map(|target| &target.music)
            .chain(self.stream.engine.pending_events())
            .filter(|event| event.phrase == phrase)
            .collect()
    }
    pub fn remaining_ms(&self, now: u64) -> Option<u64> {
        if !self.automatic {
            None
        } else if self.paused {
            Some(self.remaining)
        } else {
            self.deadline.map(|d| d.saturating_sub(now))
        }
    }
    pub fn elapsed_ms(&self, now: u64) -> u64 {
        now.saturating_sub(self.started)
            .saturating_sub(self.paused_ms)
            .saturating_sub(if self.paused {
                now.saturating_sub(self.paused_at)
            } else {
                0
            })
    }
    fn finish(&mut self, outcome: Outcome, now: u64) {
        if self.attempts[self.index].is_none() {
            let extra = if self.paused {
                now.saturating_sub(self.paused_at)
            } else {
                0
            };
            self.attempts[self.index] = Some(Attempt {
                outcome,
                elapsed_ms: now
                    .saturating_sub(self.turn_started)
                    .saturating_sub(self.turn_pause + extra),
                limit_ms: self.turn_limit,
            });
        }
    }
    fn enter(&mut self, index: usize, now: u64) {
        if index == self.history.len() {
            self.history.push(self.stream.next_target());
            self.attempts.push(None);
        }
        self.index = index;
        self.turn_started = now;
        self.turn_pause = 0;
        self.remaining = (self.seconds * 1000.0).round() as u64;
        self.turn_limit = self.automatic.then_some(self.remaining);
        self.deadline = self.automatic.then_some(now + self.remaining);
        if self.paused {
            self.paused_ms += now.saturating_sub(self.paused_at);
            self.paused_at = now;
        }
    }
    fn advance(&mut self, outcome: Outcome, now: u64) {
        self.finish(outcome, now);
        self.enter(self.index + 1, now);
    }
    /// All inputs in one poll batch target the same event ID: never credit/skip its successor.
    pub fn apply(&mut self, action: Action, now: u64, expected_id: usize) -> bool {
        if self.stopped {
            return false;
        }
        if action == Action::Stop {
            let outcome = if !self.paused && self.deadline.is_some_and(|d| now >= d) {
                Outcome::TimedOut
            } else {
                Outcome::Stopped
            };
            self.finish(outcome, now);
            self.stopped = true;
            return true;
        }
        if self.target().music.id != expected_id {
            return false;
        }
        if !self.paused && self.deadline.is_some_and(|d| now >= d) {
            self.advance(Outcome::TimedOut, now);
            return true; // even Space at the deadline does not score the next event
        }
        match action {
            Action::Confirm if !self.paused => self.advance(Outcome::Confirmed, now),
            Action::MidiMatch if !self.paused => self.advance(Outcome::MidiMatched, now),
            Action::Next => self.advance(Outcome::Skipped, now),
            Action::Previous if self.index > 0 => {
                self.finish(Outcome::Skipped, now);
                self.enter(self.index - 1, now);
            }
            Action::Faster => {
                self.seconds = (self.seconds - self.timing.speed_step).max(self.timing.min_seconds)
            }
            Action::Slower => {
                self.seconds = (self.seconds + self.timing.speed_step).min(self.timing.max_seconds)
            }
            Action::Pause => self.pause(now),
            Action::ModulateBalanced | Action::ModulateBack => {
                let kind = if action == Action::ModulateBalanced {
                    ManualModulation::Balanced
                } else {
                    ManualModulation::Back
                };
                self.stream.engine.request_manual(kind, expected_id);
            }
            Action::ToggleAuto => {
                self.automatic = !self.automatic;
                self.remaining = (self.seconds * 1000.0).round() as u64;
                self.turn_limit = self.automatic.then_some(self.remaining);
                self.deadline = self.automatic.then_some(now + self.remaining);
            }
            _ => return false,
        }
        true
    }
    fn pause(&mut self, now: u64) {
        if self.paused {
            let delta = now - self.paused_at;
            self.paused_ms += delta;
            self.turn_pause += delta;
            self.deadline = self.automatic.then_some(now + self.remaining);
        } else {
            self.remaining = self.deadline.map_or(0, |d| d.saturating_sub(now));
            self.paused_at = now;
        }
        self.paused = !self.paused;
    }
    pub fn summary(&self, now: u64) -> Summary {
        let count = |outcome| {
            self.attempts
                .iter()
                .flatten()
                .filter(|a| a.outcome == outcome)
                .count()
        };
        let confirmed = count(Outcome::Confirmed);
        let midi_matched = count(Outcome::MidiMatched);
        let timed_out = count(Outcome::TimedOut);
        let skipped = count(Outcome::Skipped);
        let stopped = count(Outcome::Stopped);
        let total = confirmed + midi_matched + timed_out + skipped;
        Summary {
            presented: self.history.len(),
            confirmed,
            midi_matched,
            timed_out,
            skipped,
            stopped,
            score: (100 * (confirmed + midi_matched))
                .checked_div(total)
                .unwrap_or(0) as u32,
            elapsed_ms: self.elapsed_ms(now),
        }
    }
}
