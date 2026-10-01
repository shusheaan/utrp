use super::tone::Tone;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Chord {
    pub root: Tone,
    pub quality: String,
    pub tones: Vec<Tone>,
    pub degrees: Vec<u8>,
}

impl Chord {
    pub fn from_tones(tones: Vec<Tone>, degrees: Vec<u8>) -> Self {
        let root = tones[0].clone();
        let intervals: Vec<u8> = tones.iter().map(|t| (t.pc + 12 - root.pc) % 12).collect();
        let quality = match intervals.as_slice() {
            [0, 4, 7] => "",
            [0, 3, 7] => "m",
            [0, 3, 6] => "dim",
            [0, 4, 8] => "aug",
            [0, 4, 7, 11] => "maj7",
            [0, 3, 7, 10] => "m7",
            [0, 4, 7, 10] => "7",
            [0, 3, 6, 10] => "m7b5",
            [0, 3, 6, 9] => "dim7",
            [0, 3, 7, 11] => "mMaj7",
            [0, 4, 8, 11] => "maj7#5",
            [0, 4, 8, 10] => "7#5",
            [0, 3, 6, 11] => "dimMaj7",
            [0, 2, 7] => "sus2",
            [0, 5, 7] => "sus4",
            [0, 4, 7, 2] => "add9",
            [0, 3, 7, 2] => "m(add9)",
            [0, 4, 11, 6] => "maj7(#11,no5)",
            _ => "(color)",
        }
        .into();
        Self {
            root,
            quality,
            tones,
            degrees,
        }
    }
    pub fn degree_label(&self, index: usize) -> String {
        let degree = self.degrees[index];
        let natural = [0_i16, 2, 4, 5, 7, 9, 11][usize::from((degree - 1) % 7)];
        let interval = i16::from((self.tones[index].pc + 12 - self.root.pc) % 12);
        let delta = (interval - natural + 6).rem_euclid(12) - 6;
        let accidental = if delta >= 0 {
            "#".repeat(delta as usize)
        } else {
            "b".repeat((-delta) as usize)
        };
        format!("{accidental}{degree}")
    }
    pub fn symbol(&self) -> String {
        format!("{}{}", self.root.name, self.quality)
    }
    pub fn pcs(&self) -> Vec<u8> {
        self.tones.iter().map(|t| t.pc).collect()
    }
    pub fn dominant(root: Tone) -> Self {
        let tones = [(0, 0), (4, 2), (7, 4), (10, 6)]
            .map(|(n, d)| root.transpose(n, d))
            .to_vec();
        Self::from_tones(tones, vec![1, 3, 5, 7])
    }
    pub fn secondary(&self) -> Self {
        Self::dominant(self.root.transpose(7, 4))
    }
    pub fn substitute(&self) -> Self {
        Self::dominant(self.root.transpose(1, 1))
    }
    pub fn tonicizable(&self) -> bool {
        matches!(
            self.quality.as_str(),
            "" | "m" | "maj7" | "m7" | "mMaj7" | "7"
        )
    }
    /// SD25: local ii7/iiø7 -> V7. SSD25: related ii7 -> subV7.
    /// The target itself is not included; diminished/augmented/colors are excluded.
    pub fn approach_ii_v(&self, substitute: bool) -> Option<[Self; 2]> {
        if !self.tonicizable() {
            return None;
        }
        let dominant = if substitute {
            self.substitute()
        } else {
            self.secondary()
        };
        let root = if substitute {
            dominant.root.transpose(7, 4)
        } else {
            self.root.transpose(2, 1)
        };
        let minor_target = matches!(self.quality.as_str(), "m" | "m7" | "mMaj7");
        let fifth = if minor_target && !substitute { 6 } else { 7 };
        let tones = [(0, 0), (3, 2), (fifth, 4), (10, 6)]
            .map(|(n, d)| root.transpose(n, d))
            .to_vec();
        Some([Self::from_tones(tones, vec![1, 3, 5, 7]), dominant])
    }
    pub fn piano_notes(&self, inversion: usize, base: u8) -> Vec<u8> {
        let mut notes = Vec::new();
        for i in 0..self.tones.len() {
            let pc = self.tones[(i + inversion) % self.tones.len()].pc;
            let mut n = base - base % 12 + pc;
            while notes.last().is_some_and(|last| n <= *last) {
                n += 12;
            }
            notes.push(n);
        }
        notes
    }
}
