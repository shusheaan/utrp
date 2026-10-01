use crate::{
    config::{Config, Templates},
    guitar::GuitarPlanner,
    progression::Progression,
    session::{PracticeStream, Target},
    theory::key::Mode,
};
use anyhow::{bail, ensure, Context, Result};
use serde_json::{json, Value};
use std::path::PathBuf;

#[derive(Debug, Default)]
pub struct Options {
    pub config: Option<PathBuf>,
    pub templates: Option<PathBuf>,
    pub instrument: Option<String>,
    pub seed: Option<u64>,
    pub measures: Option<usize>,
    pub key: Option<String>,
    pub mode: Option<Mode>,
    pub threshold: Option<usize>,
    pub base: Option<u8>,
    pub headless: bool,
}
impl Options {
    pub fn parse(args: &[String]) -> Result<Self> {
        let mut result = Self::default();
        let mut i = 0;
        while i < args.len() {
            let arg = &args[i];
            if arg == "simulate" || arg == "--headless" {
                result.headless = true;
                i += 1;
                continue;
            }
            let value = args
                .get(i + 1)
                .with_context(|| format!("missing value for {arg}"))?;
            match arg.as_str() {
                "--config" => result.config = Some(value.into()),
                "--templates" => result.templates = Some(value.into()),
                "--instrument" | "--difficulty" => {
                    ensure!(
                        matches!(value.as_str(), "guitar" | "piano"),
                        "instrument must be guitar or piano"
                    );
                    result.instrument = Some(value.clone());
                }
                "--seed" => result.seed = Some(value.parse()?),
                "--measures" | "--events" => {
                    let n = value.parse()?;
                    ensure!(n > 0, "event count must be positive");
                    result.measures = Some(n);
                }
                "--key" => result.key = Some(value.clone()),
                "--mode" => {
                    result.mode = Some(serde_json::from_value(json!(value.replace('-', "_")))?)
                }
                "--threshold" => {
                    let n = value.parse()?;
                    ensure!(n > 0, "threshold must be positive");
                    result.threshold = Some(n);
                }
                "--base" => {
                    let n = value.parse()?;
                    ensure!((24..=72).contains(&n), "base must be 24..72");
                    result.base = Some(n);
                }
                _ => bail!("unknown argument {arg}; see --help"),
            }
            i += 2;
        }
        Ok(result)
    }
    pub fn load(&self) -> Result<(Config, Templates, u64)> {
        let mut config = Config::load(self.config.as_deref())?;
        if let Some(key) = &self.key {
            config.simulation.keys = vec![key.clone()];
        }
        if let Some(mode) = self.mode {
            config.simulation.modes = vec![mode];
        }
        if let Some(n) = self.threshold {
            config.simulation.minimum_phrases_in_key = n;
        }
        let env_seed = std::env::var("UTRP_SIM_SEED")
            .ok()
            .map(|s| s.parse::<u64>())
            .transpose()
            .context("invalid UTRP_SIM_SEED")?;
        let seed = self
            .seed
            .or(config.simulation.seed)
            .or(env_seed)
            .unwrap_or_else(rand::random);
        config.simulation.seed = Some(seed);
        config.validate()?;
        let templates = Templates::load(self.templates.as_deref())?;
        Ok((config, templates, seed))
    }
}
pub fn stream(
    config: &Config,
    templates: Templates,
    seed: u64,
    base: u8,
) -> Result<PracticeStream> {
    config.validate()?;
    ensure!((24..=72).contains(&base), "base must be 24..72");
    let engine = Progression::new(config.simulation.clone(), templates, seed)?;
    Ok(PracticeStream::new(
        engine,
        GuitarPlanner::new(config.guitar.clone()),
        base,
    ))
}
pub fn export(target: &Target, instrument: &str) -> Value {
    let event = &target.music;
    let notes = if instrument == "guitar" {
        if target.guitar.task == "arpeggio_detached" {
            if target.guitar.arpeggio.len() == event.chord.tones.len() {
                target.guitar.arpeggio.iter().map(|p| p.midi).collect()
            } else {
                Vec::new()
            }
        } else {
            target
                .guitar
                .shape
                .as_ref()
                .map(|s| s.positions.iter().map(|p| p.midi).collect::<Vec<_>>())
                .unwrap_or_default()
        }
    } else {
        target.piano_notes.clone()
    };
    json!({"measure":event.id,"key":event.key.label(),"modulation":event.role,"degree":event.degree,"scale":event.key.scale().iter().map(|t|t.pc).collect::<Vec<_>>(),
        "chords":[{"role":"target","kind":event.role,"symbol":event.chord.symbol(),"root_pc":event.chord.root.pc,"notes":notes}],"event":target})
}
pub fn run(options: &Options) -> Result<()> {
    let (config, templates, seed) = options.load()?;
    let mut generator = stream(&config, templates, seed, options.base.unwrap_or(48))?;
    let output: Vec<Value> = (0..options.measures.unwrap_or(24))
        .map(|_| {
            export(
                &generator.next_target(),
                options.instrument.as_deref().unwrap_or("piano"),
            )
        })
        .collect();
    serde_json::to_writer_pretty(std::io::stdout().lock(), &output)?;
    Ok(())
}
