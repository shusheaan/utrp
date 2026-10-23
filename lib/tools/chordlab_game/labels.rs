//! Shared notation semantics with the JSFX capsule: degree, symbol, bass (chord tone).
use utrp::progression::ChordEvent;

pub fn kind(event: &ChordEvent) -> u32 {
    match event.role.as_str() {
        "secondary" | "substitute" | "sd25_ii" | "sd25_v" | "ssd25_ii" | "ssd25_v" => 1,
        "shared_pivot" | "diminished_pivot" | "bridge" => 2,
        "arrival" | "mode_change" => 3,
        _ => 0,
    }
}

/// Fixed-major palette for real targets; target-relative degree for approaches.
/// Tritone substitution is bII (green), not mislabeled V (orange).
pub fn capsule(event: &ChordEvent, resolution: &ChordEvent) -> (String, i32) {
    let letter = |s: &str| "CDEFGAB".find(s.chars().next().unwrap()).unwrap() as i32;
    let relative = kind(event) == 1;
    let tonic = if relative {
        &resolution.chord.root
    } else {
        &event.key.tonic
    };
    let degree_index = (letter(&event.chord.root.name) - letter(&tonic.name)).rem_euclid(7);
    let index = if relative {
        degree_index
    } else {
        // The left-hand palette is fixed to the relative major, not rebased on minor I.
        (degree_index
            + if event.key.mode == utrp::theory::key::Mode::Aeolian {
                5
            } else {
                0
            })
            % 7
    };
    let role = [0, 1, 1, 2, 2, 3, 3][index as usize];
    let roman = if relative {
        let mut local = event.clone();
        local.key.tonic = resolution.chord.root.clone();
        local.key.mode = utrp::theory::key::Mode::Ionian;
        degree(&local)
    } else {
        degree(event)
    };
    (format!("{roman} {}", event.chord.symbol()), role)
}

pub fn degree(event: &ChordEvent) -> String {
    let root_letter = event.chord.root.name.chars().next().expect("spelled chord");
    let scale = event.key.scale();
    let index = scale
        .iter()
        .position(|t| t.name.starts_with(root_letter))
        .expect("scale letter");
    let delta =
        (i32::from(event.chord.root.pc) - i32::from(scale[index].pc) + 6).rem_euclid(12) - 6;
    let accidental = if delta < 0 {
        "b".repeat((-delta) as usize)
    } else {
        "#".repeat(delta as usize)
    };
    let minor = matches!(
        event.chord.quality.as_str(),
        "m7" | "m7b5" | "dim7" | "mMaj7" | "dimMaj7"
    );
    let roman = ["I", "II", "III", "IV", "V", "VI", "VII"][index];
    let roman = if minor {
        roman.to_lowercase()
    } else {
        roman.into()
    };
    let suffix = match event.chord.quality.as_str() {
        "m7b5" => "ø",
        "dim7" | "dimMaj7" => "°",
        "maj7#5" | "7#5" => "+",
        _ => "",
    };
    format!("{accidental}{roman}{suffix}")
}

pub fn action(event: &ChordEvent) -> &'static str {
    match event.role.as_str() {
        "secondary" => "Approach: secondary V7",
        "substitute" => "Approach: tritone subV7",
        "sd25_ii" => "Approach: local ii7",
        "sd25_v" => "Approach: local V7",
        "ssd25_ii" => "Approach: substitute ii7",
        "ssd25_v" => "Approach: substitute V7",
        "shared_pivot" => "Modulate: shared 7th",
        "diminished_pivot" => "Modulate: diminished 7th",
        "bridge" => "Modulate: destination V7",
        "arrival" => "Arrival: new tonic",
        "mode_change" => "Arrival: same tonic, new mode",
        "minor_dominant" => "Backbone: minor V7 -> i7",
        _ => "Backbone: stay in key",
    }
}
