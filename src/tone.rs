use std::fmt;
use log::{debug, info};
use colored::*;
use crate::{chord::ChordType, key::KeyType};

#[derive(Debug, Clone)]
pub(super) enum Interval {
    PerfectUnison,
    MinorSecond,
    MajorSecond,
    MinorThird,
    MajorThird,
    PerfectFourth,
    AugmentedFourth,
    DiminishedFifth,
    PerfectFifth,
    MinorSixth,
    MajorSixth,
    MinorSeventh,
    MajorSeventh,
}

impl fmt::Display for Interval {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Interval::PerfectUnison => {write!(f, "PerfectUnison")},
            Interval::MinorSecond => {write!(f, "MinorSecond")},
            Interval::MajorSecond => {write!(f, "MajorSecond")},
            Interval::MinorThird => {write!(f, "MinorThird")},
            Interval::MajorThird => {write!(f, "MajorThird")},
            Interval::PerfectFourth => {write!(f, "PerfectFourth")},
            Interval::AugmentedFourth => {write!(f, "AugmentedFourth")},
            Interval::DiminishedFifth => {write!(f, "DiminishedFifth")},
            Interval::PerfectFifth => {write!(f, "PerfectFifth")},
            Interval::MinorSixth => {write!(f, "MinorSixth")},
            Interval::MajorSixth => {write!(f, "MajorSixth")},
            Interval::MinorSeventh => {write!(f, "MinorSeventh")},
            Interval::MajorSeventh => {write!(f, "MajorSeventh")},
        }
    }
}

impl Interval {
    fn key_diff(&self) -> i8 {
        match self {
            Interval::PerfectUnison => 0,
            Interval::MinorSecond => 1,
            Interval::MajorSecond => 2,
            Interval::MinorThird => 3,
            Interval::MajorThird => 4,
            Interval::PerfectFourth => 5,
            Interval::AugmentedFourth => 6,
            Interval::DiminishedFifth => 6,
            Interval::PerfectFifth => 7,
            Interval::MinorSixth => 8,
            Interval::MajorSixth => 9,
            Interval::MinorSeventh => 10,
            Interval::MajorSeventh => 11,
        }
    }

    fn tone_diff(&self) -> i8 {
        match self {
            Interval::PerfectUnison => 0,
            Interval::MinorSecond => 1,
            Interval::MajorSecond => 1,
            Interval::MinorThird => 2,
            Interval::MajorThird => 2,
            Interval::PerfectFourth => 3,
            Interval::AugmentedFourth => 3,
            Interval::DiminishedFifth => 4,
            Interval::PerfectFifth => 4,
            Interval::MinorSixth => 5,
            Interval::MajorSixth => 5,
            Interval::MinorSeventh => 6,
            Interval::MajorSeventh => 6,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) enum NeutralTone {C, D, E, F, G, A, B}

impl fmt::Display for NeutralTone {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            NeutralTone::C => {write!(f, "{}", "C".green().bold().italic())},
            NeutralTone::D => {write!(f, "{}", "D".blue().bold().italic())},
            NeutralTone::E => {write!(f, "{}", "E".cyan().bold().italic())},
            NeutralTone::F => {write!(f, "{}", "F".green().bold().italic())},
            NeutralTone::G => {write!(f, "{}", "G".yellow().bold().italic())},
            NeutralTone::A => {write!(f, "{}", "A".blue().bold().italic())},
            NeutralTone::B => {write!(f, "{}", "B".purple().bold().italic())},
        }
    }
}

impl NeutralTone {
    fn derived_vec(&self) -> Vec<Self> {
        match self {
            NeutralTone::C => {
                vec![
                    NeutralTone::C,
                    NeutralTone::D,
                    NeutralTone::E,
                    NeutralTone::F,
                    NeutralTone::G,
                    NeutralTone::A,
                    NeutralTone::B,
            ]},
            NeutralTone::D => {
                vec![
                    NeutralTone::D,
                    NeutralTone::E,
                    NeutralTone::F,
                    NeutralTone::G,
                    NeutralTone::A,
                    NeutralTone::B,
                    NeutralTone::C,
            ]},
            NeutralTone::E => {
                vec![
                    NeutralTone::E,
                    NeutralTone::F,
                    NeutralTone::G,
                    NeutralTone::A,
                    NeutralTone::B,
                    NeutralTone::C,
                    NeutralTone::D,
            ]},
            NeutralTone::F => {
                vec![
                    NeutralTone::F,
                    NeutralTone::G,
                    NeutralTone::A,
                    NeutralTone::B,
                    NeutralTone::C,
                    NeutralTone::D,
                    NeutralTone::E,
            ]},
            NeutralTone::G => {
                vec![
                    NeutralTone::G,
                    NeutralTone::A,
                    NeutralTone::B,
                    NeutralTone::C,
                    NeutralTone::D,
                    NeutralTone::E,
                    NeutralTone::F,
            ]},
            NeutralTone::A => {
                vec![
                    NeutralTone::A,
                    NeutralTone::B,
                    NeutralTone::C,
                    NeutralTone::D,
                    NeutralTone::E,
                    NeutralTone::F,
                    NeutralTone::G,
            ]},
            NeutralTone::B => {
                vec![
                    NeutralTone::B,
                    NeutralTone::C,
                    NeutralTone::D,
                    NeutralTone::E,
                    NeutralTone::F,
                    NeutralTone::G,
                    NeutralTone::A,
            ]},
        }
    }

    fn add_interval(&self, interval: &Interval) -> Self {
        let v = self.derived_vec();
        v[interval.tone_diff() as usize].clone()
    }

    fn minus_interval(&self, interval: &Interval) -> Self {
        let mut v = self.derived_vec();
        let diff = interval.tone_diff();
        match diff {
            0 => v[0].clone(),
            x => v[v.len()-(x as usize)].clone(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ToneVariant {Flat, Neutral, Sharp}

impl fmt::Display for ToneVariant {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            ToneVariant::Sharp => {write!(f, "{}", "#".white().bold())},
            ToneVariant::Neutral => {write!(f, "")},
            ToneVariant::Flat => {write!(f, "{}", "b".white().bold())},
        }
    }
}

#[derive(Clone, PartialEq, Eq)]
pub struct Tone {
    pub(super) idx: i8, // 1-12
    tone: NeutralTone,
    variant: ToneVariant,
}

impl Tone {
    pub(super) fn new(tone: NeutralTone, variant: ToneVariant) -> Self {
        let idx = Self::tone_idx(&tone, &variant);
        Tone {idx, tone, variant}
    }

    pub(super) fn rematch_key(self, key_type: &KeyType) -> Tone {
        let tonics = Vec::from([
            Tone::new(NeutralTone::C, ToneVariant::Neutral),
            Tone::new(NeutralTone::D, ToneVariant::Flat),
            Tone::new(NeutralTone::D, ToneVariant::Neutral),
            Tone::new(NeutralTone::E, ToneVariant::Flat),
            Tone::new(NeutralTone::E, ToneVariant::Neutral),
            Tone::new(NeutralTone::F, ToneVariant::Neutral),
            Tone::new(NeutralTone::F, ToneVariant::Sharp),
            Tone::new(NeutralTone::G, ToneVariant::Flat),
            Tone::new(NeutralTone::G, ToneVariant::Neutral),
            Tone::new(NeutralTone::A, ToneVariant::Flat),
            Tone::new(NeutralTone::A, ToneVariant::Neutral),
            Tone::new(NeutralTone::B, ToneVariant::Flat),
            Tone::new(NeutralTone::B, ToneVariant::Neutral),
        ]);
        let interval = match key_type {
            KeyType::Ionian => Interval::PerfectUnison,
            KeyType::Dorian => Interval::MajorSecond,
            KeyType::Phrygian => Interval::MajorThird,
            KeyType::Lydian => Interval::PerfectFourth,
            KeyType::Mixolydian => Interval::PerfectFifth,
            KeyType::Aeolian => Interval::MajorSixth,
            KeyType::Locrian => Interval::MajorSeventh,
        };
        info!("Tone::rematch_key(): {} applied for {}", interval, key_type);
        let tonics: Vec<Tone> = tonics
            .into_iter()
            .map(|e| e.add_interval(interval.clone()))
            .collect();

        let mut matched_tonic;
        if tonics.contains(&self) {
            matched_tonic = self;
        } else {
            matched_tonic = tonics
                .into_iter()
                .filter(|e| e.idx==self.idx)
                .collect::<Vec<Tone>>()[0].clone();
        }
        matched_tonic
    }

    pub(super) fn rematch_interval(self, interval: &Interval) -> Tone {
        let key_type = match interval {
            Interval::PerfectUnison | Interval::MajorSecond
                | Interval::MajorThird | Interval::PerfectFourth
                | Interval::PerfectFifth | Interval::MajorSixth
                | Interval::MajorSeventh => {KeyType::Ionian},
            Interval::MinorSecond | Interval::MinorSixth
                => {KeyType::Phrygian},
            Interval::MinorThird | Interval::MinorSeventh
                => {KeyType::Dorian},
            Interval::AugmentedFourth => {KeyType::Lydian},
            Interval::DiminishedFifth => {KeyType::Locrian},
        };
        self.rematch_key(&key_type)
    }

    pub(super) fn rematch_diminished(self) -> Tone {
        let tonics = Vec::from([
            Tone::new(NeutralTone::C, ToneVariant::Neutral),
            Tone::new(NeutralTone::C, ToneVariant::Sharp),
            Tone::new(NeutralTone::D, ToneVariant::Neutral),
            Tone::new(NeutralTone::D, ToneVariant::Sharp),
            Tone::new(NeutralTone::E, ToneVariant::Neutral),
            Tone::new(NeutralTone::F, ToneVariant::Neutral),
            Tone::new(NeutralTone::F, ToneVariant::Sharp),
            Tone::new(NeutralTone::G, ToneVariant::Neutral),
            Tone::new(NeutralTone::G, ToneVariant::Sharp),
            Tone::new(NeutralTone::A, ToneVariant::Neutral),
            Tone::new(NeutralTone::B, ToneVariant::Flat),
            Tone::new(NeutralTone::B, ToneVariant::Neutral),
        ]);
        let mut matched_tonic;
        if tonics.contains(&self) {
            matched_tonic = self;
        } else {
            matched_tonic = tonics
                .into_iter()
                .filter(|e| e.idx==self.idx)
                .collect::<Vec<Tone>>()[0].clone();
        }
        matched_tonic
    }

    pub(super) fn rematch_chord(self, chord_type: &ChordType) -> Tone {
        let key_type = match chord_type {
            ChordType::Major7 => KeyType::Ionian,
            ChordType::Minor7 => KeyType::Dorian,
            ChordType::Dominant7 => KeyType::Mixolydian,
            ChordType::HalfDiminished7 => KeyType::Locrian,
            ChordType::Diminished7 => KeyType::Ionian,
        };
        self.rematch_key(&key_type)
    }

    fn tone_idx(tone: &NeutralTone, variant: &ToneVariant) -> i8 {
        match tone {
            NeutralTone::C => {
                match variant {
                    ToneVariant::Flat => 12,
                    ToneVariant::Neutral => 1,
                    ToneVariant::Sharp => 2,
                }
            },
            NeutralTone::D => {
                match variant {
                    ToneVariant::Flat => 2,
                    ToneVariant::Neutral => 3,
                    ToneVariant::Sharp => 4,
                }
            },
            NeutralTone::E => {
                match variant {
                    ToneVariant::Flat => 4,
                    ToneVariant::Neutral => 5,
                    ToneVariant::Sharp => 6,
                }
            },
            NeutralTone::F => {
                match variant {
                    ToneVariant::Flat => 5,
                    ToneVariant::Neutral => 6,
                    ToneVariant::Sharp => 7,
                }
            },
            NeutralTone::G => {
                match variant {
                    ToneVariant::Flat => 7,
                    ToneVariant::Neutral => 8,
                    ToneVariant::Sharp => 9,
                }
            },
            NeutralTone::A => {
                match variant {
                    ToneVariant::Flat => 9,
                    ToneVariant::Neutral => 10,
                    ToneVariant::Sharp => 11,
                }
            },
            NeutralTone::B => {
                match variant {
                    ToneVariant::Flat => 11,
                    ToneVariant::Neutral => 12,
                    ToneVariant::Sharp => 1,
                }
            },
        }
    }

    pub(super) fn add_interval(&self, interval: Interval) -> Tone {
        let mut idx = (self.idx + interval.key_diff()) % 12;
        if idx == 0 {idx = 12;}
        let target = self.tone.add_interval(&interval);
        let matches = gen_tones(idx)
            .into_iter()
            .filter(|e| e.tone==target)
            .collect::<Vec<Tone>>();

        debug!("adding {:?}:{} to {}:{}, tgt {}, from {:?} found {:?}",
            interval, interval.key_diff(), self, self.idx, target, gen_tones(idx), matches,
        );

        if matches.len() == 0 {panic!("tone not available")}
        matches[0].clone()
    }

    fn minus_interval(&self, interval: Interval) -> Tone {
        let mut idx = self.idx - interval.key_diff();
        if idx < 0 {idx += 12};

        let target = self.tone.minus_interval(&interval);
        let matches = gen_tones(idx)
            .into_iter()
            .filter(|e| e.tone==target)
            .collect::<Vec<Tone>>();
        if matches.len() == 0 {panic!("tone not available")}
        matches[0].clone()
    }
}

impl fmt::Display for Tone {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}{}", self.tone, self.variant)
    }
}

impl fmt::Debug for Tone {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}{}", self.tone, self.variant)
    }
}

fn gen_tones(idx: i8) -> Vec<Tone> {
    match idx {
        1 => {vec!(
            Tone {idx: 1, tone: NeutralTone::B, variant: ToneVariant::Sharp},
            Tone {idx: 1, tone: NeutralTone::C, variant: ToneVariant::Neutral},
        )},
        2 => {vec!(
            Tone {idx: 2, tone: NeutralTone::C, variant: ToneVariant::Sharp},
            Tone {idx: 2, tone: NeutralTone::D, variant: ToneVariant::Flat},
        )},
        3 => {vec!(
            Tone {idx: 3, tone: NeutralTone::D, variant: ToneVariant::Neutral},
        )},
        4 => {vec!(
            Tone {idx: 4, tone: NeutralTone::D, variant: ToneVariant::Sharp},
            Tone {idx: 4, tone: NeutralTone::E, variant: ToneVariant::Flat},
        )},
        5 => {vec!(
            Tone {idx: 5, tone: NeutralTone::E, variant: ToneVariant::Neutral},
            Tone {idx: 5, tone: NeutralTone::F, variant: ToneVariant::Flat},
        )},
        6 => {vec!(
            Tone {idx: 6, tone: NeutralTone::E, variant: ToneVariant::Sharp},
            Tone {idx: 6, tone: NeutralTone::F, variant: ToneVariant::Neutral},
        )},
        7 => {vec!(
            Tone {idx: 7, tone: NeutralTone::F, variant: ToneVariant::Sharp},
            Tone {idx: 7, tone: NeutralTone::G, variant: ToneVariant::Flat},
        )},
        8 => {vec!(
            Tone {idx: 8, tone: NeutralTone::G, variant: ToneVariant::Neutral},
        )},
        9 => {vec!(
            Tone {idx: 9, tone: NeutralTone::G, variant: ToneVariant::Sharp},
            Tone {idx: 9, tone: NeutralTone::A, variant: ToneVariant::Flat},
        )},
        10 => {vec!(
            Tone {idx: 10, tone: NeutralTone::A, variant: ToneVariant::Neutral},
        )},
        11 => {vec!(
            Tone {idx: 11, tone: NeutralTone::A, variant: ToneVariant::Sharp},
            Tone {idx: 11, tone: NeutralTone::B, variant: ToneVariant::Flat},
        )},
        12 => {vec!(
            Tone {idx: 12, tone: NeutralTone::B, variant: ToneVariant::Neutral},
            Tone {idx: 12, tone: NeutralTone::C, variant: ToneVariant::Flat},
        )},
        _ => {panic!("key idx not valid")}
    }
}
