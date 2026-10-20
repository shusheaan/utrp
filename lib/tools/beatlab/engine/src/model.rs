use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Options {
    pub bpm: f64,
    pub bars: u32,
    pub gate_db: f64,
}
impl Options {
    pub fn validate(&self) -> Result<(), String> {
        if !self.bpm.is_finite()
            || !(40.0..=240.0).contains(&self.bpm)
            || !(1..=8).contains(&self.bars)
            || !self.gate_db.is_finite()
            || !(-60.0..=-12.0).contains(&self.gate_db)
        {
            return Err("Expected BPM 40..240, bars 1..8, gate -60..-12 dBFS".into());
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Event {
    pub beat: f64,
    pub source_sample: u64,
    /// Version 2: 0..3 are categories; 4 is Review. Version 1: 3 is Review.
    pub class: u8,
    pub velocity: u8,
    /// Separation score, NOT a calibrated probability of correctness.
    pub confidence: f64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Pattern {
    pub version: u32,
    pub bpm: f64,
    pub bars: u32,
    pub sample_rate: u32,
    pub notes: Vec<u8>,
    /// Steps per quarter: 0=off; 2/4/8/16=straight, 3/6/12=triplets.
    pub grid: u32,
    pub strength: f64,
    pub events: Vec<Event>,
}
impl Pattern {
    pub fn validate(&self) -> Result<(), String> {
        Options {
            bpm: self.bpm,
            bars: self.bars,
            gate_db: -36.0,
        }
        .validate()?;
        if ![1, 2].contains(&self.version)
            || self.notes.len() != if self.version == 1 { 3 } else { 4 }
            || !(8_000..=192_000).contains(&self.sample_rate)
            || ![0, 2, 3, 4, 6, 8, 12, 16].contains(&self.grid)
            || !self.strength.is_finite()
            || !(0.0..=1.0).contains(&self.strength)
            || self.notes.iter().any(|n| *n > 127)
            || self.events.len() > 2048
        {
            return Err("Invalid pattern settings or too many events".into());
        }
        let samples = self.bars as f64 * 4.0 * 60.0 / self.bpm * self.sample_rate as f64;
        if self.events.iter().any(|e| {
            !e.beat.is_finite()
                || e.beat < 0.0
                || e.beat >= self.bars as f64 * 4.0
                || e.class as usize > self.notes.len()
                || e.velocity == 0
                || e.velocity > 127
                || !e.confidence.is_finite()
                || !(0.0..=1.0).contains(&e.confidence)
                || e.source_sample > samples.ceil() as u64
        }) {
            return Err("Invalid note event".into());
        }
        Ok(())
    }
}
