use std::collections::BTreeSet;
use utrp::{
    config::{Config, Templates},
    progression::Progression,
};

fn engine(seed: u64, probability: f64, approaches: bool) -> Progression {
    let mut p = Progression::new(
        Config::load(None).unwrap().simulation,
        Templates::load(None).unwrap(),
        seed,
    )
    .unwrap();
    p.enable_seventh_practice(4).unwrap();
    p.configure_practice(probability, approaches).unwrap();
    p
}

#[test]
fn random_start_preserves_original_cycle() {
    let cycle = Templates::load(None).unwrap().cycle;
    let mut starts = BTreeSet::new();
    for seed in 0..32 {
        let mut p = engine(seed, 0.0, false);
        let first = p.next_event();
        let start = first.cycle.unwrap().step - 1;
        starts.insert(start);
        assert!(start < cycle.len() - 1);
        assert_eq!(first.degree, Some(cycle[start]));
    }
    assert!(starts.len() > 10);
}

#[test]
fn timeout_or_missing_degree_never_unlocks_modulation() {
    for missing in 0..=7 {
        let mut p = engine(13, 1.0, true);
        let first = p.next_event();
        let key = first.key;
        for _ in 0..500 {
            let e = p.next_event();
            assert_eq!(e.key, key);
            assert_eq!(e.chord.tones.len(), 4);
            p.acknowledge_practice(&e, missing != 0 && e.degree != Some(missing));
        }
    }
}

#[test]
fn seven_successes_unlock_before_full_lap_and_every_event_is_seventh() {
    for seed in 0..32 {
        let mut p = engine(seed, 1.0, false);
        let mut key = None;
        let mut covered = 0u8;
        let mut changes = 0;
        let mut first_change = None;
        for index in 0..240 {
            let e = p.next_event();
            assert_eq!(e.chord.tones.len(), 4, "{}", e.role);
            if key.as_ref().is_some_and(|k| *k != e.key) {
                assert_eq!(covered, 127);
                covered = 0;
                changes += 1;
                first_change.get_or_insert(index);
            }
            key = Some(e.key.clone());
            if e.cycle.is_some() {
                covered |= 1 << (e.degree.unwrap() - 1);
            }
            p.acknowledge_practice(&e, true);
        }
        assert!(changes > 3);
        assert!(first_change.unwrap() < 40);
    }
}

#[test]
fn zero_probability_stays_in_key_after_coverage() {
    let mut p = engine(1, 0.0, true);
    let key = p.next_event().key;
    for _ in 0..500 {
        let e = p.next_event();
        assert_eq!(e.key, key);
        p.acknowledge_practice(&e, true);
    }
}
