use crate::theory::{key::Mode, tone::Tone};
use anyhow::{ensure, Context, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Config {
    pub session: Timing,
    pub simulation: Simulation,
    pub guitar: Guitar,
    pub storage: Storage,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Timing {
    pub seconds_per_chord: f64,
    pub speed_step: f64,
    pub min_seconds: f64,
    pub max_seconds: f64,
    pub automatic: bool,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Simulation {
    #[serde(default)]
    pub progression: ProgressionKind,
    #[serde(default = "default_chunk_size")]
    pub cycle_chunk_size: usize,
    #[serde(default)]
    pub minor_dominant_probability: f64,
    pub seed: Option<u64>,
    pub keys: Vec<String>,
    pub modes: Vec<Mode>,
    pub seventh_probability: f64,
    pub modulation_probability: f64,
    #[serde(default = "default_modulation_methods")]
    pub modulation_methods: Vec<ModulationMethod>,
    #[serde(default)]
    pub modulation_return_probability: f64,
    #[serde(default = "default_key_balance_tolerance")]
    pub key_balance_tolerance: usize,
    pub minimum_phrases_in_key: usize,
    pub extensions: bool,
    #[serde(default)]
    pub approaches: bool,
    pub secondary_probability: f64,
    pub substitution_probability: f64,
    #[serde(default)]
    pub sd25_probability: f64,
    #[serde(default)]
    pub ssd25_probability: f64,
    pub borrow_probability: f64,
    pub ambient: bool,
    pub ambient_probability: f64,
}
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ProgressionKind {
    OriginalCycle,
    #[default]
    ModalPhrases,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ModulationMethod {
    Dominant,
    SharedChord,
    Diminished,
}
fn default_modulation_methods() -> Vec<ModulationMethod> {
    // Existing custom configs retain their previous behavior.
    vec![ModulationMethod::Dominant]
}
fn default_key_balance_tolerance() -> usize {
    40
}
fn default_region_stay() -> usize {
    1
}
fn default_chunk_size() -> usize {
    4
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Guitar {
    pub tuning: [u8; 6],
    pub max_fret: u8,
    pub max_span: u8,
    pub regions: Vec<[u8; 2]>,
    pub triad_strings: Vec<Vec<u8>>,
    pub seventh_strings: Vec<Vec<u8>>,
    pub arpeggio_every: usize,
    #[serde(default = "default_region_stay")]
    pub phrases_per_region: usize,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Storage {
    pub enabled: bool,
    pub directory: Option<PathBuf>,
}
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Templates {
    #[serde(default)]
    pub cycle: Vec<u8>,
    pub templates: Vec<Template>,
}
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Template {
    pub mode: Mode,
    pub phrases: Vec<Vec<u8>>,
}

impl Config {
    pub fn load(path: Option<&Path>) -> Result<Self> {
        let text = match path {
            Some(p) => {
                std::fs::read_to_string(p).with_context(|| format!("read {}", p.display()))?
            }
            None => include_str!("../config/simulate.toml").into(),
        };
        let cfg: Self = toml::from_str(&text).context("invalid simulate config")?;
        cfg.validate()?;
        Ok(cfg)
    }
    pub fn validate(&self) -> Result<()> {
        let t = &self.session;
        ensure!(
            [
                t.seconds_per_chord,
                t.speed_step,
                t.min_seconds,
                t.max_seconds
            ]
            .iter()
            .all(|v| v.is_finite() && *v > 0.0),
            "timings must be finite and positive"
        );
        ensure!(
            t.min_seconds <= t.seconds_per_chord
                && t.seconds_per_chord <= t.max_seconds
                && t.max_seconds <= 86400.0,
            "invalid timing bounds"
        );
        ensure!(
            t.min_seconds >= 0.001 && t.speed_step >= 0.001,
            "timing resolution is one millisecond"
        );
        let s = &self.simulation;
        s.validate_modulation_methods()?;
        s.validate_approaches()?;
        ensure!(
            !s.keys.is_empty() && !s.modes.is_empty(),
            "keys/modes cannot be empty"
        );
        for key in &s.keys {
            Tone::parse(key)?;
        }
        ensure!(
            s.minimum_phrases_in_key > 0,
            "minimum_phrases_in_key must be positive"
        );
        ensure!(
            (1..=8).contains(&s.cycle_chunk_size),
            "cycle_chunk_size must be 1..8"
        );
        for p in [
            s.minor_dominant_probability,
            s.seventh_probability,
            s.modulation_probability,
            s.modulation_return_probability,
            s.secondary_probability,
            s.substitution_probability,
            s.borrow_probability,
            s.ambient_probability,
        ] {
            ensure!(
                p.is_finite() && (0.0..=1.0).contains(&p),
                "probability outside [0,1]"
            );
        }
        let g = &self.guitar;
        ensure!(
            (1..=100).contains(&g.phrases_per_region),
            "phrases_per_region must be 1..100"
        );
        ensure!(
            g.max_fret <= 36 && g.max_span > 0 && g.max_span <= 6,
            "invalid guitar fret/span limits"
        );
        ensure!(
            g.tuning
                .iter()
                .all(|n| u16::from(*n) + u16::from(g.max_fret) <= 127),
            "guitar pitches exceed MIDI"
        );
        ensure!(
            g.tuning.windows(2).all(|w| w[0] < w[1]),
            "tuning must be ascending low to high"
        );
        ensure!(
            !g.regions.is_empty() && g.regions.iter().all(|r| r[0] <= r[1] && r[1] <= g.max_fret),
            "invalid regions"
        );
        for (sets, size) in [(&g.triad_strings, 3), (&g.seventh_strings, 4)] {
            ensure!(!sets.is_empty(), "empty string sets");
            for set in sets {
                ensure!(
                    set.len() == size
                        && set.iter().all(|s| (1..=6).contains(s))
                        && set.windows(2).all(|w| w[0] > w[1]),
                    "string sets must be descending unique string numbers with {size} entries"
                );
            }
        }
        Ok(())
    }
}
impl Simulation {
    pub(crate) fn validate_approaches(&self) -> Result<()> {
        let probabilities = [
            self.secondary_probability,
            self.substitution_probability,
            self.sd25_probability,
            self.ssd25_probability,
            self.borrow_probability,
        ];
        ensure!(
            probabilities
                .iter()
                .all(|p| p.is_finite() && (0.0..=1.0).contains(p)),
            "approach/borrow probabilities must be in [0,1]"
        );
        ensure!(
            probabilities.iter().sum::<f64>() <= 1.0,
            "approach/borrow probabilities must sum to <= 1"
        );
        Ok(())
    }
    pub(crate) fn validate_modulation_methods(&self) -> Result<()> {
        ensure!(
            self.modulation_return_probability.is_finite()
                && (0.0..=1.0).contains(&self.modulation_return_probability),
            "modulation_return_probability must be in [0,1]"
        );
        ensure!(
            !self.modulation_methods.is_empty(),
            "modulation_methods cannot be empty"
        );
        for (i, method) in self.modulation_methods.iter().enumerate() {
            ensure!(
                !self.modulation_methods[..i].contains(method),
                "duplicate modulation method"
            );
        }
        Ok(())
    }
}
impl Templates {
    pub fn load(path: Option<&Path>) -> Result<Self> {
        let text = match path {
            Some(p) => std::fs::read_to_string(p)?,
            None => include_str!("../config/progressions.toml").into(),
        };
        let result: Self = toml::from_str(&text)?;
        result.validate()?;
        Ok(result)
    }
    pub fn validate(&self) -> Result<()> {
        ensure!(
            self.cycle.is_empty()
                || (self.cycle.len() >= 3
                    && self.cycle.first() == Some(&1)
                    && self.cycle.last() == Some(&1)
                    && self.cycle.iter().all(|d| (1..=7).contains(d))),
            "cycle must start/end on degree 1 with valid degrees"
        );
        for t in &self.templates {
            ensure!(!t.phrases.is_empty(), "empty templates");
            ensure!(
                t.phrases.iter().all(|p| p.len() >= 3
                    && p.first() == Some(&1)
                    && p.last() == Some(&1)
                    && p.iter().all(|d| (1..=7).contains(d))),
                "phrases must begin/end on degree 1 with valid degrees"
            );
        }
        Ok(())
    }
}
