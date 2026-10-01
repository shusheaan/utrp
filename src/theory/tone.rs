use anyhow::{bail, Result};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Tone {
    pub pc: u8,
    pub name: String,
}

impl Tone {
    /// Scientific pitch label with the chord's spelling, including B# / Cb
    /// octave boundaries. The caller supplies an actual occurrence of this tone.
    pub fn midi_label(&self, midi: u8) -> String {
        assert_eq!(midi % 12, self.pc, "MIDI note must match tone");
        let accidental: i16 = self
            .name
            .chars()
            .skip(1)
            .map(|c| match c {
                '#' => 1,
                'b' => -1,
                _ => 0,
            })
            .sum();
        let octave = (i16::from(midi) - accidental).div_euclid(12) - 1;
        format!("{}{octave}", self.name)
    }
    pub fn parse(name: &str) -> Result<Self> {
        let mut chars = name.chars();
        let base: i16 = match chars.next() {
            Some('C') => 0,
            Some('D') => 2,
            Some('E') => 4,
            Some('F') => 5,
            Some('G') => 7,
            Some('A') => 9,
            Some('B') => 11,
            _ => bail!("invalid note: {name}"),
        };
        let accidental: String = chars.collect();
        let offset = match accidental.as_str() {
            "" => 0,
            "#" => 1,
            "##" => 2,
            "b" => -1,
            "bb" => -2,
            _ => bail!("invalid accidental: {name}"),
        };
        Ok(Self {
            pc: (base + offset).rem_euclid(12) as u8,
            name: name.into(),
        })
    }

    pub fn transpose(&self, semitones: u8, diatonic_steps: usize) -> Self {
        let letters = ['C', 'D', 'E', 'F', 'G', 'A', 'B'];
        let bases = [0_i16, 2, 4, 5, 7, 9, 11];
        let index = letters
            .iter()
            .position(|c| self.name.starts_with(*c))
            .expect("validated tone");
        let next = (index + diatonic_steps) % 7;
        let pc = (self.pc + semitones) % 12;
        let delta = (i16::from(pc) - bases[next] + 6).rem_euclid(12) - 6;
        let accidental = if delta >= 0 {
            "#".repeat(delta as usize)
        } else {
            "b".repeat((-delta) as usize)
        };
        Self {
            pc,
            name: format!("{}{accidental}", letters[next]),
        }
    }
}

pub fn midi_name(note: u8) -> String {
    let names = [
        "C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B",
    ];
    format!(
        "{}{}",
        names[(note % 12) as usize],
        i16::from(note) / 12 - 1
    )
}
