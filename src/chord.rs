use colored::*;
use log::info;
use rand::{
    distributions::{Distribution, Standard},
    prelude::*,
    Rng,
};
use rand_chacha::ChaCha8Rng;
use statrs::distribution::Categorical;
use std::{error::Error, fmt};

use crate::{
    app::Difficulty,
    key::{Key, KeyType},
    tone::{Interval, Tone},
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
            ChordType::Major7 => {
                write!(f, "{}", "M7".green().bold())
            }
            ChordType::Minor7 => {
                write!(f, "{}", "m7".blue().bold())
            }
            ChordType::Dominant7 => {
                write!(f, "{}", "7".yellow().bold())
            }
            ChordType::HalfDiminished7 => {
                write!(f, "{}", "m7b5".purple().bold())
            }
            ChordType::Diminished7 => {
                write!(f, "{}", "dim7".red().bold())
            }
        }
    }
}

#[derive(Debug, Clone)]
pub(super) enum Inversion {
    PianoOriginal,
    PianoFirst,
    PianoSecond,
    PianoThird,
    GuitarFirst,
    GuitarSecond,
    GuitarThird,
    GuitarFourth,
    GuitarFifth,
}

impl fmt::Display for Inversion {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Inversion::PianoOriginal => {
                write!(f, "{}", "p/0".white().bold())
            }
            Inversion::PianoFirst => {
                write!(f, "{}", "p/1".green().bold())
            }
            Inversion::PianoSecond => {
                write!(f, "{}", "p/2".blue().bold())
            }
            Inversion::PianoThird => {
                write!(f, "{}", "p/3".cyan().bold())
            }
            Inversion::GuitarFirst => {
                write!(f, "{}", "g/1".green().bold())
            }
            Inversion::GuitarSecond => {
                write!(f, "{}", "g/2".blue().bold())
            }
            Inversion::GuitarThird => {
                write!(f, "{}", "g/3".cyan().bold())
            }
            Inversion::GuitarFourth => {
                write!(f, "{}", "g/4".purple().bold())
            }
            Inversion::GuitarFifth => {
                write!(f, "{}", "g/5".yellow().bold())
            }
        }
    }
}

impl Inversion {
    pub(super) fn sample(difficulty: Difficulty) -> anyhow::Result<Self> {
        // let mut rng_seed = ChaCha8Rng::seed_from_u64(42);
        let mut rng_seed = rand::thread_rng();
        let prob = match difficulty {
            Difficulty::Piano => [1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            Difficulty::Guitar => [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        };

        let mnm = Categorical::new(&prob)?;
        Ok(match mnm.sample(&mut rng_seed) as i32 {
            0 => Inversion::PianoOriginal,
            1 => Inversion::PianoFirst,
            2 => Inversion::PianoSecond,
            3 => Inversion::PianoThird,
            4 => Inversion::GuitarFirst,
            5 => Inversion::GuitarSecond,
            6 => Inversion::GuitarThird,
            7 => Inversion::GuitarFourth,
            8 => Inversion::GuitarFifth,
            _ => panic!("random error"),
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
    pub(super) fn new(mut tonic: Tone, chord_type: ChordType, inversion: Inversion) -> Self {
        info!("Chord::new(): build {}{}", tonic, chord_type);
        match chord_type {
            ChordType::Diminished7 => {
                tonic = tonic.rematch_diminished();
            }
            _ => {
                tonic = tonic.rematch_chord(&chord_type);
            }
        };
        let (third, fifth, seventh) = match chord_type {
            ChordType::Major7 => (
                tonic.add_interval(Interval::MajorThird),
                tonic.add_interval(Interval::PerfectFifth),
                tonic.add_interval(Interval::MajorSeventh),
            ),
            ChordType::Minor7 => (
                tonic.add_interval(Interval::MinorThird),
                tonic.add_interval(Interval::PerfectFifth),
                tonic.add_interval(Interval::MinorSeventh),
            ),
            ChordType::Dominant7 => (
                tonic.add_interval(Interval::MajorThird),
                tonic.add_interval(Interval::PerfectFifth),
                tonic.add_interval(Interval::MinorSeventh),
            ),
            ChordType::HalfDiminished7 => (
                tonic.add_interval(Interval::MinorThird),
                tonic.add_interval(Interval::DiminishedFifth),
                tonic.add_interval(Interval::MinorSeventh),
            ),
            ChordType::Diminished7 => (
                tonic.add_interval(Interval::MinorThird),
                tonic.add_interval(Interval::DiminishedFifth),
                tonic.add_interval(Interval::MajorSixth),
            ),
        };

        let tones = match inversion {
            Inversion::PianoOriginal => {
                vec![tonic.clone(), third, fifth, seventh]
            }
            Inversion::PianoFirst => {
                vec![third, fifth, seventh, tonic.clone()]
            }
            Inversion::PianoSecond => {
                vec![fifth, seventh, tonic.clone(), third]
            }
            Inversion::PianoThird => {
                vec![seventh, tonic.clone(), third, fifth]
            }
            Inversion::GuitarFirst => {
                vec![
                    tonic.clone(),
                    fifth.clone(),
                    seventh,
                    third,
                    fifth,
                    tonic.clone(),
                ]
            }
            Inversion::GuitarSecond => {
                vec![
                    fifth.clone(),
                    tonic.clone(),
                    fifth.clone(),
                    seventh,
                    third,
                    fifth,
                ]
            }
            Inversion::GuitarThird => {
                vec![fifth.clone(), tonic.clone(), fifth, seventh, third]
            }
            Inversion::GuitarFourth => {
                vec![seventh.clone(), third, fifth, tonic.clone(), seventh]
            }
            Inversion::GuitarFifth => {
                vec![seventh, third, fifth, tonic.clone()]
            }
        };
        Chord {
            tonic,
            chord_type,
            inversion,
            tones,
        }
    }

    fn gen_diminished(&self, difficulty: Difficulty) -> anyhow::Result<Chord> {
        let matched_tonic = self.tonic.clone().rematch_diminished();
        Ok(Chord::new(
            matched_tonic,
            ChordType::Diminished7,
            Inversion::sample(difficulty)?,
        ))
    }

    pub(super) fn gen_secondary_dominant(&self, difficulty: Difficulty) -> anyhow::Result<Chord> {
        let chord_type = ChordType::Dominant7;
        let matched_tonic = self.tonic.clone().rematch_chord(&chord_type);
        Ok(Chord::new(
            matched_tonic.add_interval(Interval::PerfectFifth),
            chord_type,
            Inversion::sample(difficulty)?,
        ))
    }

    pub(super) fn gen_substitute_sd(&self, difficulty: Difficulty) -> anyhow::Result<Chord> {
        let chord_type = ChordType::Dominant7;
        let matched_tonic = self.tonic.clone().rematch_chord(&chord_type);
        Ok(Chord::new(
            matched_tonic.add_interval(Interval::MajorSecond),
            chord_type,
            Inversion::sample(difficulty)?,
        ))
    }

    pub(super) fn gen_second_minor(&self, difficulty: Difficulty) -> anyhow::Result<Chord> {
        let chord_type = ChordType::Minor7;
        let matched_tonic = self.tonic.clone().rematch_chord(&chord_type);
        Ok(Chord::new(
            matched_tonic.add_interval(Interval::PerfectFifth),
            chord_type,
            Inversion::sample(difficulty)?,
        ))
    }

    pub(super) fn gen_major_keys(&self) -> Vec<Key> {
        let int_tonic_vec: Vec<Interval> = match self.chord_type {
            ChordType::Major7 => Vec::from([Interval::PerfectUnison, Interval::PerfectFifth]),
            ChordType::Minor7 => Vec::from([
                Interval::MinorSeventh,
                Interval::MinorSixth,
                Interval::MinorThird,
            ]),
            ChordType::Dominant7 => Vec::from([Interval::PerfectFourth]),
            ChordType::HalfDiminished7 => Vec::from([Interval::MinorSecond]),
            ChordType::Diminished7 => Vec::from([
                Interval::MinorSecond,
                Interval::MajorThird,
                Interval::PerfectFifth,
                Interval::MinorSeventh,
            ]),
        };

        let mut keys = Vec::new();
        for int_tonic in int_tonic_vec.into_iter() {
            let matched_tonic = self.tonic.clone().rematch_interval(&int_tonic);
            let new_tonic = matched_tonic.add_interval(int_tonic);

            let key_type = KeyType::Ionian;
            let matched_new_tonic = new_tonic.clone().rematch_key(&key_type);
            keys.push(Key::new(new_tonic, key_type));
        }
        keys
    }
}

impl fmt::Display for Chord {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(
            f,
            "{}{}-{}: {:?}",
            self.tonic, self.chord_type, self.inversion, self.tones
        )
    }
}

impl fmt::Debug for Chord {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(
            f,
            "{}{}-{}: {:?}",
            self.tonic, self.chord_type, self.inversion, self.tones
        )
    }
}
