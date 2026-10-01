//! Finite detached paths: cyclic chord-member orders × actual positions.
//! Releasing each note allows repeated strings; this is not a held grip.
use crate::{config::Guitar, guitar::Position, theory::chord::Chord};

pub fn member_positions(chord: &Chord, cfg: &Guitar, region: [u8; 2]) -> Vec<Vec<Position>> {
    chord
        .tones
        .iter()
        .enumerate()
        .map(|(index, tone)| {
            (1..=6)
                .flat_map(|string| (region[0]..=region[1]).map(move |fret| (string, fret)))
                .filter_map(|(string, fret)| {
                    let midi = cfg.tuning[usize::from(6 - string)] + fret;
                    (midi % 12 == tone.pc).then_some(Position {
                        string,
                        fret,
                        midi,
                        degree: chord.degrees[index],
                        finger: None,
                    })
                })
                .collect()
        })
        .collect()
}

/// Visit ordinal enumerates every cyclic starting member and fret-product once
/// before repeating. Odd visits choose a nearby path, even visits explore.
pub fn path(chord: &Chord, cfg: &Guitar, region: [u8; 2], visit: usize) -> Vec<Position> {
    let positions = member_positions(chord, cfg, region);
    if positions.iter().any(Vec::is_empty) {
        return Vec::new();
    }
    let ordinal = visit / 2;
    let start = ordinal % positions.len();
    let mut encoded = ordinal / positions.len();
    let mut result: Vec<Position> = Vec::new();
    for step in 0..positions.len() {
        let choices = &positions[(start + step) % positions.len()];
        let selected = if visit.is_multiple_of(2) || result.is_empty() {
            &choices[encoded % choices.len()]
        } else {
            let previous = result.last().expect("not empty");
            choices
                .iter()
                .min_by_key(|p| {
                    (
                        p.midi.abs_diff(previous.midi),
                        p.string.abs_diff(previous.string),
                    )
                })
                .expect("positions validated")
        };
        encoded /= choices.len();
        result.push(selected.clone());
    }
    result
}
