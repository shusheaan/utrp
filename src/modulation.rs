use colored::*;
use log::info;
use rand::{
    distributions::{Distribution, Standard},
    prelude::*,
    Rng,
};
use rand_chacha::ChaCha8Rng;
use statrs::distribution::Categorical;
use std::fmt;

use crate::{app::Difficulty, chord::Chord};

pub(super) enum DeTour {
    Straight,
    SecondaryDominant,
    SubstituteSD,
    SD25,
    SSD25,
}

impl fmt::Display for DeTour {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            DeTour::Straight => {
                write!(f, "{}", "Straight".white().bold())
            }
            DeTour::SecondaryDominant => {
                write!(f, "{}", "SecondaryDominant".green().bold())
            }
            DeTour::SubstituteSD => {
                write!(f, "{}", "SubstituteSD".blue().bold())
            }
            DeTour::SD25 => {
                write!(f, "{}", "SD25".red().bold())
            }
            DeTour::SSD25 => {
                write!(f, "{}", "SSD25".purple().bold())
            }
        }
    }
}

impl DeTour {
    pub(super) fn sample(difficulty: Difficulty) -> anyhow::Result<Self> {
        // let mut rng_seed = ChaCha8Rng::seed_from_u64(42);
        let mut rng_seed = rand::thread_rng();
        let prob = match difficulty {
            Difficulty::Easy => [1.0, 1.0, 1.0, 1.0, 1.0],
            Difficulty::Hell => [5.0, 3.0, 3.0, 1.0, 1.0],
            Difficulty::Guitar => [1.0; 5],
        };

        let mnm = Categorical::new(&prob)?;
        let detour = match mnm.sample(&mut rng_seed) as i32 {
            0 => DeTour::Straight,
            1 => DeTour::SecondaryDominant,
            2 => DeTour::SubstituteSD,
            3 => DeTour::SD25,
            4 => DeTour::SSD25,
            _ => panic!("random error"),
        };
        info!("DeTour::sample(): {} sampled", detour);
        Ok(detour)
    }

    pub(super) fn build_chords(
        &self,
        chord: Chord,
        difficulty: Difficulty,
    ) -> anyhow::Result<Vec<Chord>> {
        match self {
            DeTour::Straight => Ok(Vec::from([chord])),
            DeTour::SecondaryDominant => {
                let pre_chord = chord.gen_secondary_dominant(difficulty)?;
                Ok(Vec::from([chord, pre_chord]))
            }
            DeTour::SubstituteSD => {
                let pre_chord = chord.gen_substitute_sd(difficulty)?;
                Ok(Vec::from([chord, pre_chord]))
            }
            DeTour::SD25 => {
                let pre_chord = chord.gen_secondary_dominant(difficulty.clone())?;
                let pp_chord = pre_chord.gen_second_minor(difficulty.clone())?;
                Ok(Vec::from([chord, pre_chord, pp_chord]))
            }
            DeTour::SSD25 => {
                let pre_chord = chord.gen_substitute_sd(difficulty.clone())?;
                let pp_chord = pre_chord.gen_second_minor(difficulty.clone())?;
                Ok(Vec::from([chord, pre_chord, pp_chord]))
            }
        }
    }
}

#[derive(Debug)]
pub enum Modulation {
    SameKey,
    ViaTonic,
    ViaSharedChord,
    ViaDiminished,
    Back,
}

impl fmt::Display for Modulation {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Modulation::SameKey => {
                write!(f, "{}", "(no key change)".white().bold())
            }
            Modulation::ViaTonic => {
                write!(
                    f,
                    "{}",
                    "(switch mode with the current key tonic)".green().bold()
                )
            }
            Modulation::ViaSharedChord => {
                write!(
                    f,
                    "{}",
                    "(to a new key sharing the current chord)".blue().bold()
                )
            }
            Modulation::ViaDiminished => {
                write!(
                    f,
                    "{}",
                    "(modulation via diminished (advanced))".cyan().bold()
                )
            }
            Modulation::Back => {
                write!(f, "{}", "(back to the previous key)".yellow().bold())
            }
        }
    }
}

impl Modulation {
    pub(super) fn sample(difficulty: Difficulty) -> anyhow::Result<Self> {
        let mut rng_seed = rand::thread_rng();

        let prob = match difficulty {
            Difficulty::Easy => [1.0; 5],
            Difficulty::Hell => [5.0, 3.0, 3.0, 3.0, 1.0],
            Difficulty::Guitar => [1.0; 5],
        };

        let mnm = Categorical::new(&prob)?;
        Ok(match mnm.sample(&mut rng_seed) as i32 {
            0 => Modulation::SameKey,
            1 => Modulation::ViaTonic,
            2 => Modulation::ViaSharedChord,
            3 => Modulation::ViaDiminished,
            4 => Modulation::Back,
            _ => panic!("random error"),
        })
    }
}
