//! Headless progression simulator over the ORIGINAL utrp theory code.
//!
//! The `theory` module below is the untouched source tree of the Rust TUI
//! (`#[path]` include — nothing copied, nothing rewritten). This binary only
//! re-creates the driver that app.rs runs interactively (Iterator::next +
//! App::modulate dispatch) minus the terminal/scoring, and prints one JSON
//! object per measure to stdout: key, modulation, detour, and the chords in
//! play order with concrete MIDI notes (ascending stack of the sampled
//! inversion). All randomness stays inside the original samplers
//! (thread_rng — runs are non-reproducible by design, same as the TUI).
//!
//! Usage: utrp-sim [--measures 24] [--threshold 4] [--difficulty piano|guitar]
//!                 [--base 48] [--key F] [--mode aeolian]

mod app {
    // shim for `crate::app::Difficulty` referenced by the theory sources
    #[derive(Debug, Clone)]
    pub enum Difficulty {
        Piano,
        Guitar,
    }
}

#[path = "../../../../src/theory/mod.rs"]
mod theory;

use app::Difficulty;
use theory::{
    chord::{Chord, ChordType, Inversion},
    key::{Key, KeyType},
    modulation::{DeTour, Modulation},
    tone::{NeutralTone, Tone, ToneVariant},
};

// the 40-step all-changes degree sequence from app.rs (data, verbatim)
const SS: [i8; 40] = [
    1, 3, 1, 4, 2, 5, 6, 3, 7, 1, 4, 5, 3, 2, 4, 7, 6, 5, 6, 1, 7, 6, 2, 4, 5, 1, 5, 3, 6, 7, 3,
    4, 2, 1, 6, 2, 7, 3, 5, 1,
];

fn arg(args: &[String], name: &str) -> Option<String> {
    args.iter()
        .position(|a| a == name)
        .and_then(|i| args.get(i + 1).cloned())
}

fn parse_key(name: &str) -> anyhow::Result<Tone> {
    let mut chars = name.chars();
    let letter = match chars.next() {
        Some('C') => NeutralTone::C,
        Some('D') => NeutralTone::D,
        Some('E') => NeutralTone::E,
        Some('F') => NeutralTone::F,
        Some('G') => NeutralTone::G,
        Some('A') => NeutralTone::A,
        Some('B') => NeutralTone::B,
        _ => anyhow::bail!("bad key: {name}"),
    };
    let variant = match chars.next() {
        None => ToneVariant::Neutral,
        Some('#') => ToneVariant::Sharp,
        Some('b') => ToneVariant::Flat,
        _ => anyhow::bail!("bad key: {name}"),
    };
    Ok(Tone::new(letter, variant))
}

fn parse_mode(name: &str) -> anyhow::Result<KeyType> {
    Ok(match name {
        "ionian" => KeyType::Ionian,
        "dorian" => KeyType::Dorian,
        "phrygian" => KeyType::Phrygian,
        "lydian" => KeyType::Lydian,
        "mixolydian" => KeyType::Mixolydian,
        "aeolian" => KeyType::Aeolian,
        "locrian" => KeyType::Locrian,
        _ => anyhow::bail!("bad mode: {name}"),
    })
}

/// Ascending MIDI stack of a chord's voicing (tones are pitch classes 1-12,
/// bass to top as the sampled inversion laid them out).
fn midi_notes(chord: &Chord, base: i32) -> Vec<i32> {
    let mut out: Vec<i32> = Vec::new();
    for tone in &chord.tones {
        let pc = (tone.idx as i32 - 1).rem_euclid(12);
        let mut note = base - 6 + (pc - (base - 6).rem_euclid(12)).rem_euclid(12);
        while let Some(&prev) = out.last() {
            if note > prev {
                break;
            }
            note += 12;
        }
        out.push(note);
    }
    out
}

fn scale_pcs(key: &Key, difficulty: &Difficulty) -> Vec<i32> {
    // key scale as pitch classes via the original chord generator roots
    (1..=7)
        .filter_map(|d| key.gen_chord(d, difficulty.clone()).ok())
        .map(|c| (c.tonic.idx as i32 - 1).rem_euclid(12))
        .collect()
}

fn esc(s: String) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

fn chord_json(chord: &Chord, role: &str, base: i32) -> String {
    let notes: Vec<String> = midi_notes(chord, base).iter().map(|n| n.to_string()).collect();
    format!(
        "{{\"role\":\"{}\",\"symbol\":\"{}\",\"notes\":[{}]}}",
        role,
        esc(format!("{}", chord)),
        notes.join(",")
    )
}

fn main() -> anyhow::Result<()> {
    colored::control::set_override(false); // plain strings in JSON
    let args: Vec<String> = std::env::args().collect();
    let measures: usize = arg(&args, "--measures").map_or(24, |v| v.parse().unwrap_or(24));
    let threshold: i32 = arg(&args, "--threshold").map_or(4, |v| v.parse().unwrap_or(4));
    let base: i32 = arg(&args, "--base").map_or(48, |v| v.parse().unwrap_or(48));
    let difficulty = match arg(&args, "--difficulty").as_deref() {
        Some("guitar") => Difficulty::Guitar,
        _ => Difficulty::Piano,
    };

    let mut current_key = match (arg(&args, "--key"), arg(&args, "--mode")) {
        (Some(k), Some(m)) => Key::new(parse_key(&k)?, parse_mode(&m)?),
        (Some(k), None) => Key::new(parse_key(&k)?, KeyType::Ionian),
        _ => Key::sample(difficulty.clone())?,
    };
    let mut prev_key = current_key.clone();
    let mut key_iteration = 1i32;
    let mut ss_idx: usize = 0;
    let mut current_chord = current_key.gen_chord(SS[ss_idx], difficulty.clone())?;

    println!("[");
    for m in 0..measures {
        // driver mirrors app.rs Iterator::next + App::modulate, calling the
        // original theory functions for every musical decision
        let modulation = if key_iteration >= threshold {
            Modulation::sample(difficulty.clone())?
        } else {
            Modulation::SameKey
        };

        let mut play_order: Vec<(String, Chord)> = Vec::new();
        match modulation {
            Modulation::SameKey => {
                key_iteration += 1;
                ss_idx = (ss_idx + 1) % SS.len();
                let detour = DeTour::sample(difficulty.clone())?;
                let chords = detour.build_chords(
                    current_key.gen_chord(SS[ss_idx], difficulty.clone())?,
                    difficulty.clone(),
                )?;
                for c in chords.iter().skip(1).rev() {
                    play_order.push(("approach".into(), c.clone()));
                }
                play_order.push(("target".into(), chords[0].clone()));
            }
            Modulation::ViaTonic => {
                prev_key = current_key.clone();
                key_iteration = 1;
                ss_idx = rand::random::<usize>() % SS.len();
                current_key = Key::new(
                    current_key.tonic.clone(),
                    KeyType::sample(difficulty.clone())?,
                );
                let detour = DeTour::sample(difficulty.clone())?;
                let chords = detour.build_chords(
                    current_key.gen_chord(SS[ss_idx], difficulty.clone())?,
                    difficulty.clone(),
                )?;
                for c in chords.iter().skip(1).rev() {
                    play_order.push(("approach".into(), c.clone()));
                }
                play_order.push(("target".into(), chords[0].clone()));
            }
            Modulation::ViaSharedChord => {
                prev_key = current_key.clone();
                key_iteration = 1;
                ss_idx = rand::random::<usize>() % SS.len();
                let hosts = current_chord.gen_major_keys();
                let host = hosts[rand::random::<usize>() % hosts.len()].clone();
                current_key = host.change_mode((rand::random::<u8>() % 7) as i8);
                let detour = DeTour::sample(difficulty.clone())?;
                let chords = detour.build_chords(
                    current_key.gen_chord(SS[ss_idx], difficulty.clone())?,
                    difficulty.clone(),
                )?;
                for c in chords.iter().skip(1).rev() {
                    play_order.push(("approach".into(), c.clone()));
                }
                play_order.push(("target".into(), chords[0].clone()));
            }
            Modulation::ViaDiminished => {
                prev_key = current_key.clone();
                key_iteration = 1;
                ss_idx = 0;
                let pivot = Chord::new(
                    current_chord.tonic.clone(),
                    ChordType::Diminished7,
                    Inversion::sample(difficulty.clone())?,
                );
                let hosts = pivot.gen_major_keys();
                let host = hosts[rand::random::<usize>() % hosts.len()].clone();
                current_key = host.change_mode((rand::random::<u8>() % 7) as i8);
                let dominant = current_key.gen_chord(5, difficulty.clone())?;
                let tonic_chord = current_key.gen_chord(1, difficulty.clone())?;
                play_order.push(("pivot".into(), pivot));
                play_order.push(("approach".into(), dominant));
                play_order.push(("target".into(), tonic_chord));
            }
            Modulation::Back => {
                let back_to = prev_key.clone();
                prev_key = current_key.clone();
                current_key = back_to;
                key_iteration = 1;
                ss_idx = rand::random::<usize>() % SS.len();
                let detour = DeTour::sample(difficulty.clone())?;
                let chords = detour.build_chords(
                    current_key.gen_chord(SS[ss_idx], difficulty.clone())?,
                    difficulty.clone(),
                )?;
                for c in chords.iter().skip(1).rev() {
                    play_order.push(("approach".into(), c.clone()));
                }
                play_order.push(("target".into(), chords[0].clone()));
            }
        }
        current_chord = play_order.last().unwrap().1.clone();

        let chords_json: Vec<String> = play_order
            .iter()
            .map(|(role, c)| chord_json(c, role, base))
            .collect();
        let pcs: Vec<String> = scale_pcs(&current_key, &difficulty)
            .iter()
            .map(|p| p.to_string())
            .collect();
        let comma = if m + 1 < measures { "," } else { "" };
        println!(
            "{{\"measure\":{},\"key\":\"{}\",\"modulation\":\"{:?}\",\"degree\":{},\"scale\":[{}],\"chords\":[{}]}}{}",
            m,
            esc(format!("{}", current_key)),
            modulation,
            SS[ss_idx],
            pcs.join(","),
            chords_json.join(","),
            comma
        );
    }
    println!("]");
    Ok(())
}
