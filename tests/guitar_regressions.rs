use std::collections::BTreeMap;
use utrp::{
    config::Config,
    guitar::{shapes, GuitarPlanner},
    progression::ChordEvent,
    theory::{
        chord::Chord,
        key::{Key, Mode},
        tone::Tone,
    },
};

fn event(phrase: usize, offset: usize) -> ChordEvent {
    let key = Key {
        tonic: Tone::parse("C").unwrap(),
        mode: Mode::Ionian,
    };
    ChordEvent {
        id: phrase * 2 + offset,
        phrase,
        chord: key.chord(1, true),
        key,
        degree: Some(1),
        role: "diatonic".into(),
        reason: "coverage regression".into(),
        previous_key: None,
        cycle: None,
    }
}

#[test]
fn each_enabled_task_rotates_every_region_without_period_locking() {
    for region_count in [1, 3, 5] {
        for every in [0, 1, 2, 3, 5, 6, 10] {
            let mut cfg = Config::load(None).unwrap().guitar;
            cfg.regions.truncate(region_count);
            cfg.arpeggio_every = every;
            cfg.phrases_per_region = 1;
            let regions = cfg.regions.clone();
            let mut planner = GuitarPlanner::new(cfg);
            let mut task_counts = BTreeMap::new();
            let mut coverage = BTreeMap::new();
            for phrase in 0..region_count * every.max(1) {
                let first = planner.target(&event(phrase, 0));
                let second = planner.target(&event(phrase, 1));
                assert_eq!(first.task, second.task, "task changed inside a phrase");
                assert_eq!(
                    first.region, second.region,
                    "region changed inside a phrase"
                );
                let expected_task = if every > 0 && (phrase + 1) % every == 0 {
                    "arpeggio_detached"
                } else {
                    "chord"
                };
                assert_eq!(first.task, expected_task);
                let ordinal = task_counts.entry(first.task.clone()).or_insert(0);
                assert_eq!(first.region, regions[*ordinal % region_count]);
                *ordinal += 1;
                *coverage.entry((first.task, first.region)).or_insert(0) += 1;
            }
            for task in ["chord", "arpeggio_detached"] {
                let enabled = match task {
                    "chord" => every != 1,
                    _ => every != 0,
                };
                for region in &regions {
                    assert_eq!(
                        coverage.contains_key(&(task.to_owned(), *region)),
                        enabled,
                        "task={task}, region={region:?}, every={every}"
                    );
                }
            }
        }
    }
}

fn chord(names: &[&str], degrees: Vec<u8>) -> Chord {
    Chord::from_tones(
        names
            .iter()
            .map(|name| Tone::parse(name).unwrap())
            .collect(),
        degrees,
    )
}

fn assert_shape_family(chord: &Chord, notes: &[u8], expected: &str) {
    let cfg = Config::load(None).unwrap().guitar;
    let candidates = shapes(chord, &cfg, [0, 5]);
    let matching: Vec<_> = candidates
        .iter()
        .filter(|s| s.positions.iter().map(|p| p.midi).collect::<Vec<_>>() == notes)
        .collect();
    assert!(
        !matching.is_empty(),
        "missing playable test shape {notes:?}"
    );
    for shape in matching {
        assert_eq!(shape.family, expected, "{} {notes:?}", chord.symbol());
    }
}

#[test]
fn add9_drop2_uses_actual_closed_pitch_order() {
    let c_add9 = chord(&["C", "E", "G", "D"], vec![1, 3, 5, 9]);
    // Closed G3 C4 D4 E4; lower the second-highest voice D4 to D3.
    assert_shape_family(&c_add9, &[50, 55, 60, 64], "drop2");
}

#[test]
fn add9_drop3_uses_actual_closed_pitch_order() {
    let d_add9 = chord(&["D", "F#", "A", "E"], vec![1, 3, 5, 9]);
    // Closed A3 D4 E4 F#4; lower the third-highest voice D4 to D3.
    assert_shape_family(&d_add9, &[50, 57, 64, 66], "drop3");
}

#[test]
fn sharp11_drop2_uses_actual_closed_pitch_order() {
    let db_color = chord(&["Db", "F", "C", "G"], vec![1, 3, 7, 11]);
    // Closed C4 Db4 F4 G4; lower the second-highest voice F4 to F3.
    assert_shape_family(&db_color, &[53, 60, 61, 67], "drop2");
}

#[test]
fn tertian_seventh_drop2_classification_is_preserved() {
    let c_maj7 = chord(&["C", "E", "G", "B"], vec![1, 3, 5, 7]);
    // Closed G3 B3 C4 E4; lower C4 to C3.
    assert_shape_family(&c_maj7, &[48, 55, 59, 64], "drop2");
}
