use colored::*;
use log::{debug, info};
use rand::{
    distributions::{Distribution, Standard},
    prelude::*,
    Rng,
};
use rand_chacha::ChaCha8Rng;
use statrs::distribution::Categorical;
use std::fmt;

use crate::{
    app::Difficulty,
    chord::{Chord, ChordType, Inversion},
    tone::{Interval, NeutralTone, Tone, ToneVariant},
};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum KeyType {
    Ionian,
    Dorian,
    Phrygian,
    Lydian,
    Mixolydian,
    Aeolian,
    Locrian,
}

impl fmt::Display for KeyType {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            KeyType::Ionian => {
                write!(f, "{}", "Ionian".green().bold().italic())
            }
            KeyType::Dorian => {
                write!(f, "{}", "Dorian".blue().bold().italic())
            }
            KeyType::Phrygian => {
                write!(f, "{}", "Phrygian".cyan().bold().italic())
            }
            KeyType::Lydian => {
                write!(f, "{}", "Lydian".green().bold().italic())
            }
            KeyType::Mixolydian => {
                write!(f, "{}", "Mixolydian".yellow().bold().italic())
            }
            KeyType::Aeolian => {
                write!(f, "{}", "Aeolian".blue().bold().italic())
            }
            KeyType::Locrian => {
                write!(f, "{}", "Locrian".purple().bold().italic())
            }
        }
    }
}

impl KeyType {
    pub fn sample(difficulty: Difficulty) -> anyhow::Result<Self> {
        // let mut rng_seed = ChaCha8Rng::seed_from_u64(42);
        let mut rng_seed = rand::thread_rng();
        let prob = match difficulty {
            Difficulty::Easy => [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            Difficulty::Hell => [1.0; 7],
            Difficulty::Guitar => [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
        };

        let mnm = Categorical::new(&prob)?;
        Ok(match mnm.sample(&mut rng_seed) as i32 {
            0 => KeyType::Ionian,
            1 => KeyType::Dorian,
            2 => KeyType::Phrygian,
            3 => KeyType::Lydian,
            4 => KeyType::Mixolydian,
            5 => KeyType::Aeolian,
            6 => KeyType::Locrian,
            _ => panic!("random error"),
        })
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) struct Key {
    pub(super) tonic: Tone,
    key_type: KeyType,
}

impl fmt::Display for Key {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{} {}", self.tonic, self.key_type)
    }
}

impl Key {
    pub(super) fn new(tonic: Tone, key_type: KeyType) -> Self {
        Key {
            tonic: tonic.rematch_key(&key_type),
            key_type,
        }
    }

    pub(super) fn sample(difficulty: Difficulty) -> anyhow::Result<Self> {
        let mut rng_seed = rand::thread_rng(); // no seed
        let prob_tonic = [1.0; 13];
        let mnm_tonic = Categorical::new(&prob_tonic)?;
        let tonic = match mnm_tonic.sample(&mut rng_seed) as i32 {
            0 => Tone::new(NeutralTone::C, ToneVariant::Neutral),
            1 => Tone::new(NeutralTone::D, ToneVariant::Neutral), // 2#
            2 => Tone::new(NeutralTone::E, ToneVariant::Neutral), // 4#
            3 => Tone::new(NeutralTone::F, ToneVariant::Sharp),   // 6#

            4 => Tone::new(NeutralTone::G, ToneVariant::Neutral), // 1#
            5 => Tone::new(NeutralTone::A, ToneVariant::Neutral), // 3#
            6 => Tone::new(NeutralTone::B, ToneVariant::Neutral), // 5#

            7 => Tone::new(NeutralTone::B, ToneVariant::Flat), // 2b
            8 => Tone::new(NeutralTone::A, ToneVariant::Flat), // 4b
            9 => Tone::new(NeutralTone::G, ToneVariant::Flat), // 6b

            10 => Tone::new(NeutralTone::F, ToneVariant::Neutral), // 1b
            11 => Tone::new(NeutralTone::E, ToneVariant::Flat),    // 3b
            12 => Tone::new(NeutralTone::D, ToneVariant::Flat),    // 5b
            _ => panic!("random error"),
        };
        let ionian = Key {
            tonic,
            key_type: KeyType::Ionian,
        };
        let prob_mode = match difficulty {
            Difficulty::Easy => [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            Difficulty::Hell => [1.0; 7],
            Difficulty::Guitar => [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
        };

        let mnm_mode = Categorical::new(&prob_mode)?;
        let mode_idx = mnm_mode.sample(&mut rng_seed) as i8;
        let new_key = ionian.change_mode(mode_idx);
        Ok(new_key)
    }

    pub(super) fn log_all_chords(&self, difficulty: Difficulty) -> anyhow::Result<()> {
        for i in 1..=7 {
            info!("{}", self.gen_chord(i, difficulty.clone())?);
        }
        Ok(())
    }

    fn gen_tone(&self, idx: i8) -> Tone {
        let interval = match idx {
            1 => Interval::PerfectUnison,
            2 => match self.key_type {
                KeyType::Ionian
                | KeyType::Lydian
                | KeyType::Mixolydian
                | KeyType::Aeolian
                | KeyType::Dorian => Interval::MajorSecond,
                KeyType::Phrygian | KeyType::Locrian => Interval::MinorSecond,
            },
            3 => match self.key_type {
                KeyType::Ionian | KeyType::Lydian | KeyType::Mixolydian => Interval::MajorThird,
                KeyType::Aeolian | KeyType::Dorian | KeyType::Locrian | KeyType::Phrygian => {
                    Interval::MinorThird
                }
            },
            4 => match self.key_type {
                KeyType::Ionian
                | KeyType::Phrygian
                | KeyType::Mixolydian
                | KeyType::Aeolian
                | KeyType::Dorian
                | KeyType::Locrian => Interval::PerfectFourth,
                KeyType::Lydian => Interval::AugmentedFourth,
            },
            5 => match self.key_type {
                KeyType::Ionian
                | KeyType::Phrygian
                | KeyType::Lydian
                | KeyType::Mixolydian
                | KeyType::Aeolian
                | KeyType::Dorian => Interval::PerfectFifth,
                KeyType::Locrian => Interval::DiminishedFifth,
            },
            6 => match self.key_type {
                KeyType::Ionian | KeyType::Lydian | KeyType::Mixolydian | KeyType::Dorian => {
                    Interval::MajorSixth
                }
                KeyType::Phrygian | KeyType::Aeolian | KeyType::Locrian => Interval::MinorSixth,
            },
            7 => match self.key_type {
                KeyType::Ionian | KeyType::Lydian => Interval::MajorSeventh,
                KeyType::Phrygian
                | KeyType::Mixolydian
                | KeyType::Aeolian
                | KeyType::Locrian
                | KeyType::Dorian => Interval::MinorSeventh,
            },
            _ => panic!("idx for getting tone not valid"),
        };
        let matched_tonic = self.tonic.clone().rematch_key(&self.key_type);
        matched_tonic.add_interval(interval)
    }

    pub(super) fn gen_chord(&self, idx: i8, difficulty: Difficulty) -> anyhow::Result<Chord> {
        info!("Key::gen_chord(): generate {}th chord for {}", idx, self);
        let chord_type = match self.key_type {
            KeyType::Ionian => match idx {
                1 | 4 => ChordType::Major7,
                2 | 3 | 6 => ChordType::Minor7,
                5 => ChordType::Dominant7,
                7 => ChordType::HalfDiminished7,
                _ => panic!("chord idx not valid"),
            },
            KeyType::Dorian => match idx {
                7 | 3 => ChordType::Major7,
                1 | 2 | 5 => ChordType::Minor7,
                4 => ChordType::Dominant7,
                6 => ChordType::HalfDiminished7,
                _ => panic!("chord idx not valid"),
            },
            KeyType::Phrygian => match idx {
                6 | 2 => ChordType::Major7,
                7 | 1 | 4 => ChordType::Minor7,
                3 => ChordType::Dominant7,
                5 => ChordType::HalfDiminished7,
                _ => panic!("chord idx not valid"),
            },
            KeyType::Lydian => match idx {
                5 | 1 => ChordType::Major7,
                6 | 7 | 3 => ChordType::Minor7,
                2 => ChordType::Dominant7,
                4 => ChordType::HalfDiminished7,
                _ => panic!("chord idx not valid"),
            },
            KeyType::Mixolydian => match idx {
                4 | 7 => ChordType::Major7,
                5 | 6 | 2 => ChordType::Minor7,
                1 => ChordType::Dominant7,
                3 => ChordType::HalfDiminished7,
                _ => panic!("chord idx not valid"),
            },
            KeyType::Aeolian => match idx {
                3 | 6 => ChordType::Major7,
                1 | 4 | 5 => ChordType::Minor7,
                7 => ChordType::Dominant7,
                2 => ChordType::HalfDiminished7,
                _ => panic!("chord idx not valid"),
            },
            KeyType::Locrian => match idx {
                2 | 5 => ChordType::Major7,
                7 | 3 | 4 => ChordType::Minor7,
                6 => ChordType::Dominant7,
                1 => ChordType::HalfDiminished7,
                _ => panic!("chord idx not valid"),
            },
        };
        Ok(Chord::new(
            self.gen_tone(idx),
            chord_type,
            Inversion::sample(difficulty)?,
        ))
    }

    pub(super) fn change_mode(&self, idx: i8) -> Key {
        let key_type = self.derived_keytype_vec()[idx as usize].clone();
        let tonic = self.gen_tone(idx + 1);
        let new_key = Key { tonic, key_type };

        debug!(
            "Key::change_mode(): change {} to {} using idx {}",
            self, new_key, idx
        );
        new_key
    }

    fn derived_keytype_vec(&self) -> Vec<KeyType> {
        match self.key_type {
            KeyType::Ionian => {
                vec![
                    KeyType::Ionian,
                    KeyType::Dorian,
                    KeyType::Phrygian,
                    KeyType::Lydian,
                    KeyType::Mixolydian,
                    KeyType::Aeolian,
                    KeyType::Locrian,
                ]
            }
            KeyType::Dorian => {
                vec![
                    KeyType::Dorian,
                    KeyType::Phrygian,
                    KeyType::Lydian,
                    KeyType::Mixolydian,
                    KeyType::Aeolian,
                    KeyType::Locrian,
                    KeyType::Ionian,
                ]
            }
            KeyType::Phrygian => {
                vec![
                    KeyType::Phrygian,
                    KeyType::Lydian,
                    KeyType::Mixolydian,
                    KeyType::Aeolian,
                    KeyType::Locrian,
                    KeyType::Ionian,
                    KeyType::Dorian,
                ]
            }
            KeyType::Lydian => {
                vec![
                    KeyType::Lydian,
                    KeyType::Mixolydian,
                    KeyType::Aeolian,
                    KeyType::Locrian,
                    KeyType::Ionian,
                    KeyType::Dorian,
                    KeyType::Phrygian,
                ]
            }
            KeyType::Mixolydian => {
                vec![
                    KeyType::Mixolydian,
                    KeyType::Aeolian,
                    KeyType::Locrian,
                    KeyType::Ionian,
                    KeyType::Dorian,
                    KeyType::Phrygian,
                    KeyType::Lydian,
                ]
            }
            KeyType::Aeolian => {
                vec![
                    KeyType::Aeolian,
                    KeyType::Locrian,
                    KeyType::Ionian,
                    KeyType::Dorian,
                    KeyType::Phrygian,
                    KeyType::Lydian,
                    KeyType::Mixolydian,
                ]
            }
            KeyType::Locrian => {
                vec![
                    KeyType::Locrian,
                    KeyType::Ionian,
                    KeyType::Dorian,
                    KeyType::Phrygian,
                    KeyType::Lydian,
                    KeyType::Mixolydian,
                    KeyType::Aeolian,
                ]
            }
        }
    }
}
