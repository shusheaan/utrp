use super::{chord::Chord, tone::Tone};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Mode {
    Ionian,
    Dorian,
    Phrygian,
    Lydian,
    Mixolydian,
    Aeolian,
    Locrian,
    HarmonicMinor,
    MelodicMinor,
}

impl Mode {
    pub fn intervals(self) -> [u8; 7] {
        match self {
            Self::Ionian => [0, 2, 4, 5, 7, 9, 11],
            Self::Dorian => [0, 2, 3, 5, 7, 9, 10],
            Self::Phrygian => [0, 1, 3, 5, 7, 8, 10],
            Self::Lydian => [0, 2, 4, 6, 7, 9, 11],
            Self::Mixolydian => [0, 2, 4, 5, 7, 9, 10],
            Self::Aeolian => [0, 2, 3, 5, 7, 8, 10],
            Self::Locrian => [0, 1, 3, 5, 6, 8, 10],
            Self::HarmonicMinor => [0, 2, 3, 5, 7, 8, 11],
            Self::MelodicMinor => [0, 2, 3, 5, 7, 9, 11],
        }
    }
    pub fn name(self) -> &'static str {
        match self {
            Self::Ionian => "ionian",
            Self::Dorian => "dorian",
            Self::Phrygian => "phrygian",
            Self::Lydian => "lydian",
            Self::Mixolydian => "mixolydian",
            Self::Aeolian => "aeolian",
            Self::Locrian => "locrian",
            Self::HarmonicMinor => "harmonic_minor",
            Self::MelodicMinor => "melodic_minor",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Key {
    pub tonic: Tone,
    pub mode: Mode,
}

impl Key {
    pub fn scale(&self) -> Vec<Tone> {
        self.mode
            .intervals()
            .iter()
            .enumerate()
            .map(|(i, n)| self.tonic.transpose(*n, i))
            .collect()
    }
    pub fn label(&self) -> String {
        format!("{} {}", self.tonic.name, self.mode.name())
    }
    pub fn chord(&self, degree: u8, seventh: bool) -> Chord {
        assert!((1..=7).contains(&degree), "internal validated degree");
        let scale = self.scale();
        let d = usize::from(degree - 1);
        let tones = (0..if seventh { 4 } else { 3 })
            .map(|i| scale[(d + 2 * i) % 7].clone())
            .collect();
        Chord::from_tones(
            tones,
            if seventh {
                vec![1, 3, 5, 7]
            } else {
                vec![1, 3, 5]
            },
        )
    }
}
