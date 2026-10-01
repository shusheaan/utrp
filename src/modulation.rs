//! Functional modulation routes. Bridge tones are explicit, not scale filters.
use crate::{
    config::ModulationMethod,
    theory::{
        chord::Chord,
        key::{Key, Mode},
    },
};

#[derive(Debug, Clone)]
pub struct Pivot {
    pub chord: Chord,
    pub old_degree: u8,
    pub new_degree: u8,
}

pub fn functional(key: &Key) -> bool {
    matches!(
        key.mode,
        Mode::Ionian | Mode::Aeolian | Mode::HarmonicMinor | Mode::MelodicMinor
    )
}

/// Match the complete triad/seventh, never a subset or a root alone.
pub fn shared_chords(old: &Key, new: &Key) -> Vec<Pivot> {
    let mut pivots = Vec::new();
    for seventh in [false, true] {
        for old_degree in 1..=7 {
            let chord = old.chord(old_degree, seventh);
            for new_degree in 1..=7 {
                let candidate = new.chord(new_degree, seventh);
                if chord.root.pc == candidate.root.pc && chord.pcs() == candidate.pcs() {
                    pivots.push(Pivot {
                        chord: candidate,
                        old_degree,
                        new_degree,
                    });
                }
            }
        }
    }
    pivots
}

/// vii°7: harmonic-minor leading-tone chord; borrowed in major.
pub fn leading_diminished(key: &Key) -> Chord {
    let root = key.tonic.transpose(11, 6);
    Chord::from_tones(
        [(0, 0), (3, 2), (6, 4), (9, 6)]
            .map(|(n, d)| root.transpose(n, d))
            .to_vec(),
        vec![1, 3, 5, 7],
    )
}

pub fn diminished_pivot(old: &Key, new: &Key) -> bool {
    if !functional(old) || !functional(new) || old.tonic.pc == new.tonic.pc {
        return false;
    }
    let mut a = leading_diminished(old).pcs();
    let mut b = leading_diminished(new).pcs();
    a.sort_unstable();
    b.sort_unstable();
    a == b
}

pub fn available_methods(
    old: &Key,
    new: &Key,
    enabled: &[ModulationMethod],
) -> Vec<ModulationMethod> {
    if !functional(new) {
        return Vec::new();
    }
    enabled
        .iter()
        .copied()
        .filter(|method| match method {
            ModulationMethod::Dominant => true,
            ModulationMethod::SharedChord => !shared_chords(old, new).is_empty(),
            ModulationMethod::Diminished => diminished_pivot(old, new),
        })
        .collect()
}
