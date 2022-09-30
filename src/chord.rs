use std::{
    fmt,
    error::Error,
};
use rand::{
    Rng,
    prelude::*,
    distributions::{Distribution, Standard},
};
use rand_chacha::ChaCha8Rng;
use statrs::distribution::Categorical;
use log::info;
use colored::*;

use crate::{
    app::Difficulty,
    key::{Key, KeyType},
    tone::{Tone, Interval},
};

#[derive(Debug, Clone)]
pub(super) enum ChordType {
    Major7,
    Minor7,
    Dominant7,
    HalfDiminished7,
    Diminished7,
}

impl fmt::Display for ChordType {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            ChordType::Major7 => {write!(f, "{}", "M7".green().bold())},
            ChordType::Minor7 => {write!(f, "{}", "m7".blue().bold())},
            ChordType::Dominant7 => {write!(f, "{}", "7".yellow().bold())},
            ChordType::HalfDiminished7 => {write!(f, "{}", "m7b5".purple().bold())},
            ChordType::Diminished7 => {write!(f, "{}", "dim7".red().bold())},
        }
    }
}

#[derive(Debug, Clone)]
pub(super) enum Inversion {
    Original,
    First,
    Second,
    Third,
}

impl fmt::Display for Inversion {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Inversion::Original => {write!(f, "{}", "org".white().bold())},
            Inversion::First => {write!(f, "{}", "1st".green().bold())},
            Inversion::Second => {write!(f, "{}", "2nd".blue().bold())},
            Inversion::Third => {write!(f, "{}", "3rd".cyan().bold())},
        }
    }
}

impl Inversion {
    pub(super) fn sample(difficulty: Difficulty) -> anyhow::Result<Self> {
        // let mut rng_seed = ChaCha8Rng::seed_from_u64(42);
        let mut rng_seed = rand::thread_rng();
        let prob = match difficulty {
            Difficulty::Easy => [1.0, 0.0, 0.0, 0.0],
            Difficulty::Hell => [1.0; 4],
        };

        let mnm = Categorical::new(&prob)?;
        Ok(match mnm.sample(&mut rng_seed) as i32 {
            0 => Inversion::Original,
            1 => Inversion::First,
            2 => Inversion::Second,
            3 => Inversion::Third,
            _ => panic!("random error")
        })
    }
}

#[derive(Clone)]
pub struct Chord {
    pub(super) tonic: Tone,
    chord_type: ChordType,
    inversion: Inversion,
    pub(super) tones: Vec<Tone>,
}

impl Chord {
    pub(super) fn new(
        mut tonic: Tone,
        chord_type: ChordType,
        inversion: Inversion,
    ) -> Self {
        info!("Chord::new(): build {}{}", tonic, chord_type);
        match chord_type {
            ChordType::Diminished7 => {
                tonic = tonic.rematch_diminished();
            },
            _ => {
                tonic = tonic.rematch_chord(&chord_type);
            }
        };
        let (third, fifth, seventh) =
            match chord_type {
                ChordType::Major7 => {(
                    tonic.add_interval(Interval::MajorThird),
                    tonic.add_interval(Interval::PerfectFifth),
                    tonic.add_interval(Interval::MajorSeventh),
                )},
                ChordType::Minor7 => {(
                    tonic.add_interval(Interval::MinorThird),
                    tonic.add_interval(Interval::PerfectFifth),
                    tonic.add_interval(Interval::MinorSeventh),
                )},
                ChordType::Dominant7 => {(
                    tonic.add_interval(Interval::MajorThird),
                    tonic.add_interval(Interval::PerfectFifth),
                    tonic.add_interval(Interval::MinorSeventh),
                )},
                ChordType::HalfDiminished7 => {(
                    tonic.add_interval(Interval::MinorThird),
                    tonic.add_interval(Interval::DiminishedFifth),
                    tonic.add_interval(Interval::MinorSeventh),
                )},
                ChordType::Diminished7 => {(
                    tonic.add_interval(Interval::MinorThird),
                    tonic.add_interval(Interval::DiminishedFifth),
                    tonic.add_interval(Interval::MajorSixth),
                )},
        };

        let tones = match inversion {
            Inversion::Original => {vec![tonic.clone(), third, fifth, seventh]},
            Inversion::First => {vec![third, fifth, seventh, tonic.clone()]},
            Inversion::Second => {vec![fifth, seventh, tonic.clone(), third]},
            Inversion::Third => {vec![seventh, tonic.clone(), third, fifth]},
        };
        Chord{tonic, chord_type, inversion, tones}
    }

    fn gen_diminished(&self, difficulty: Difficulty) -> anyhow::Result<Chord> {
        let matched_tonic = self.tonic.clone()
            .rematch_diminished();
        Ok(Chord::new(
            matched_tonic,
            ChordType::Diminished7,
            Inversion::sample(difficulty)?,
        ))
    }

    pub(super) fn gen_secondary_dominant(&self, difficulty: Difficulty) -> anyhow::Result<Chord> {
        let chord_type = ChordType::Dominant7;
        let matched_tonic = self.tonic.clone()
            .rematch_chord(&chord_type);
        Ok(Chord::new(
            matched_tonic
                .add_interval(Interval::PerfectFifth),
            chord_type,
            Inversion::sample(difficulty)?,
        ))
    }

    pub(super) fn gen_substitute_sd(&self, difficulty: Difficulty) -> anyhow::Result<Chord> {
        let chord_type = ChordType::Dominant7;
        let matched_tonic = self.tonic.clone()
            .rematch_chord(&chord_type);
        Ok(Chord::new(
            matched_tonic
                .add_interval(Interval::MajorSecond),
            chord_type,
            Inversion::sample(difficulty)?,
        ))
    }

    pub(super) fn gen_second_minor(&self, difficulty: Difficulty) -> anyhow::Result<Chord> {
        let chord_type = ChordType::Minor7;
        let matched_tonic = self.tonic.clone()
            .rematch_chord(&chord_type);
        Ok(Chord::new(
            matched_tonic
                .add_interval(Interval::PerfectFifth),
            chord_type,
            Inversion::sample(difficulty)?,
        ))
    }

    pub(super) fn gen_major_keys(&self) -> Vec<Key> {
        let int_tonic_vec: Vec<Interval> =
            match self.chord_type {
                ChordType::Major7 => {
                    Vec::from([
                        Interval::PerfectUnison,
                        Interval::PerfectFifth,
                    ])
                },
                ChordType::Minor7 => {
                    Vec::from([
                        Interval::MinorSeventh,
                        Interval::MinorSixth,
                        Interval::MinorThird,
                    ])
                },
                ChordType::Dominant7 => {
                    Vec::from([
                        Interval::PerfectFourth,
                    ])
                },
                ChordType::HalfDiminished7 => {
                    Vec::from([
                        Interval::MinorSecond,
                    ])
                },
                ChordType::Diminished7 => {
                    Vec::from([
                        Interval::MinorSecond,
                        Interval::MajorThird,
                        Interval::PerfectFifth,
                        Interval::MinorSeventh,
                    ])
                },
        };

        let mut keys = Vec::new();
        for int_tonic in int_tonic_vec.into_iter() {
            let matched_tonic = self.tonic.clone().rematch_interval(&int_tonic);
            let new_tonic = matched_tonic.add_interval(int_tonic);

            let key_type = KeyType::Ionian;
            let matched_new_tonic = new_tonic.clone().rematch_key(&key_type);
            keys.push(Key::new(
                new_tonic,
                key_type
            ));
        }
        keys
    }
}

impl fmt::Display for Chord {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}{}-{}: {:?}", self.tonic, self.chord_type, self.inversion, self.tones)
    }
}

impl fmt::Debug for Chord {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}{}-{}: {:?}", self.tonic, self.chord_type, self.inversion, self.tones)
    }
}
