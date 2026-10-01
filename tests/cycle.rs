use std::collections::{BTreeMap, BTreeSet};
use utrp::{
    config::{Config, ProgressionKind, Templates},
    progression::{ChordEvent, Progression},
    simulator,
    theory::key::Mode,
};

const ORIGINAL: [u8; 40] = [
    1, 3, 1, 4, 2, 5, 6, 3, 7, 1, 4, 5, 3, 2, 4, 7, 6, 5, 6, 1, 7, 6, 2, 4, 5, 1, 5, 3, 6, 7, 3, 4,
    2, 1, 6, 2, 7, 3, 5, 1,
];
fn clean(mode: Mode) -> Config {
    let mut c = Config::load(None).unwrap();
    c.simulation.keys = vec!["A".into()];
    c.simulation.modes = vec![mode];
    c.simulation.extensions = false;
    c.simulation.approaches = false;
    c.simulation.sd25_probability = 0.0;
    c.simulation.ssd25_probability = 0.0;
    c.simulation.ambient = false;
    c.simulation.modulation_probability = 0.0;
    c.simulation.minor_dominant_probability = 0.0;
    c
}
fn engine(c: Config) -> Progression {
    Progression::new(c.simulation, Templates::load(None).unwrap(), 42).unwrap()
}

#[test]
fn daily_defaults_are_two_modes_and_core_chords() {
    let c = Config::load(None).unwrap();
    assert_eq!(c.simulation.keys.len(), 12);
    assert_eq!(c.simulation.modes, [Mode::Ionian, Mode::Aeolian]);
    assert_eq!(c.simulation.progression, ProgressionKind::OriginalCycle);
    assert!(!c.simulation.extensions && !c.simulation.ambient);
    assert_eq!(Templates::load(None).unwrap().cycle, ORIGINAL);
}

#[test]
fn original_sequence_and_every_edge_survive_all_chunk_sizes_and_lap_boundaries() {
    for mode in [Mode::Ionian, Mode::Aeolian] {
        for chunk in 1..=8 {
            let mut c = clean(mode);
            c.simulation.cycle_chunk_size = chunk;
            let mut p = engine(c);
            let expected: Vec<_> = ORIGINAL
                .iter()
                .chain(ORIGINAL[1..].iter().cycle().take(390))
                .copied()
                .collect();
            for (index, degree) in expected.iter().enumerate() {
                let event = p.next_event();
                assert_eq!(event.degree, Some(*degree));
                let pos = event.cycle.unwrap();
                let step = if index < 40 {
                    index + 1
                } else {
                    (index - 40) % 39 + 2
                };
                let lap = if index < 40 { 1 } else { (index - 40) / 39 + 2 };
                assert_eq!((pos.step, pos.lap, pos.total), (step, lap, 40));
            }
        }
    }
}

#[test]
fn modulation_waits_for_closure_and_arrival_is_new_opening_tonic() {
    let mut c = Config::load(None).unwrap();
    c.simulation.approaches = false; // Isolate bare backbone; approaches have a separate chain test.
    c.simulation.modulation_probability = 1.0;
    c.simulation.minimum_phrases_in_key = 1;
    let mut p = engine(c);
    let mut previous: Option<ChordEvent> = None;
    let mut changes = 0;
    let mut cycles = 0;
    for _ in 0..4000 {
        let event = p.next_event();
        if event.previous_key.is_some() && previous.as_ref().is_some_and(|e| e.key != event.key) {
            let prior = previous.as_ref().unwrap();
            assert_eq!(prior.cycle.as_ref().unwrap().step, 40);
            assert_eq!(prior.degree, Some(1));
            assert_eq!(event.previous_key.as_ref(), Some(&prior.key));
            changes += 1;
        }
        if let Some(pos) = &event.cycle {
            assert_eq!(event.degree, Some(ORIGINAL[pos.step - 1]));
            if let Some(prior) = &previous {
                if let Some(old) = &prior.cycle {
                    assert_eq!(old.step + 1, pos.step);
                    assert_eq!(prior.key, event.key);
                } else {
                    assert_eq!(prior.role, "bridge");
                    assert_eq!(pos.step, 1);
                }
            }
            cycles += usize::from(pos.step == 40);
        }
        previous = Some(event);
    }
    assert!(changes > 80 && cycles > 80);
}

#[test]
fn minor_v7_resolves_across_chunks_without_color_or_inserted_approach() {
    let mut c = clean(Mode::Aeolian);
    c.simulation.cycle_chunk_size = 1;
    c.simulation.minor_dominant_probability = 1.0;
    c.simulation.extensions = true;
    c.simulation.secondary_probability = 1.0;
    c.simulation.substitution_probability = 0.0;
    c.simulation.borrow_probability = 0.0;
    c.simulation.ambient = true;
    c.simulation.ambient_probability = 1.0;
    let mut p = engine(c);
    let mut found = 0;
    for _ in 0..500 {
        let e = p.next_event();
        if e.role == "minor_dominant" {
            assert_eq!(e.chord.symbol(), "E7");
            assert_eq!(e.chord.tones[1].name, "G#");
            assert_eq!(e.degree, Some(5));
            let next = p.next_event();
            assert_eq!(next.key, e.key);
            assert_eq!(next.role, "diatonic");
            assert_eq!(next.degree, Some(1));
            assert!(matches!(next.chord.quality.as_str(), "m" | "m7"));
            found += 1;
        }
    }
    assert!(found > 5);
}

#[test]
fn disabled_minor_dominant_retains_natural_minor_and_extensions_keep_backbone() {
    let mut c = clean(Mode::Aeolian);
    c.simulation.extensions = true;
    c.simulation.secondary_probability = 1.0;
    c.simulation.substitution_probability = 0.0;
    c.simulation.borrow_probability = 0.0;
    let mut p = engine(c);
    let mut seen = Vec::new();
    let mut previous_was_backbone = false;
    let mut direct = 0;
    while seen.len() < 40 {
        let e = p.next_event();
        assert_ne!(e.role, "minor_dominant");
        let backbone = e.cycle.is_some();
        if backbone {
            direct += usize::from(previous_was_backbone);
            seen.push(e.degree.unwrap());
            if e.degree == Some(5) {
                assert!(matches!(e.chord.quality.as_str(), "m" | "m7"));
            }
        }
        previous_was_backbone = backbone;
    }
    assert_eq!(seen, ORIGINAL);
    assert!(
        direct < 39,
        "inserted approaches must not count as direct backbone edges"
    );
}

#[test]
fn modal_options_do_not_relabel_original_cycle_as_modal_function() {
    let mut c = clean(Mode::Dorian);
    let mut p = engine(c.clone());
    assert!((0..100).all(|_| p.next_event().cycle.is_none()));
    c.simulation.modes = vec![Mode::Ionian];
    c.simulation.progression = ProgressionKind::ModalPhrases;
    let mut p = engine(c);
    assert!((0..100).all(|_| p.next_event().cycle.is_none()));
}

#[test]
fn invalid_cycle_configuration_fails_explicitly() {
    let c = Config::load(None).unwrap();
    for cycle in [vec![], vec![1, 2], vec![1, 8, 1]] {
        let mut t = Templates::load(None).unwrap();
        t.cycle = cycle;
        assert!(Progression::new(c.simulation.clone(), t, 42).is_err());
    }
    for chunk in [0, 9] {
        let mut c = c.clone();
        c.simulation.cycle_chunk_size = chunk;
        assert!(c.validate().is_err());
    }
    for stay in [0, 101] {
        let mut c = c.clone();
        c.guitar.phrases_per_region = stay;
        assert!(c.validate().is_err());
    }
    let mut c = c;
    c.simulation.minor_dominant_probability = f64::NAN;
    assert!(c.validate().is_err());
}

#[test]
fn default_cycle_covers_each_key_edge_and_each_task_degree_region() {
    let c = Config::load(None).unwrap();
    let mut stream = simulator::stream(&c, Templates::load(None).unwrap(), 42, 48).unwrap();
    let expected_edges: BTreeSet<_> = ORIGINAL.windows(2).map(|p| (p[0], p[1])).collect();
    assert_eq!(expected_edges.len(), 29);
    let mut edges: BTreeMap<String, BTreeSet<(u8, u8)>> = BTreeMap::new();
    let mut task_degree_region = BTreeSet::new();
    let mut previous: Option<ChordEvent> = None;
    for _ in 0..100_000 {
        let target = stream.next_target();
        let e = target.music;
        if e.cycle.is_some() {
            task_degree_region.insert((
                e.key.label(),
                target.guitar.task,
                e.degree.unwrap(),
                target.guitar.region,
            ));
            if let Some(p) = &previous {
                if p.key == e.key && p.cycle.is_some() {
                    let edge = (p.degree.unwrap(), e.degree.unwrap());
                    assert!(expected_edges.contains(&edge));
                    edges.entry(e.key.label()).or_default().insert(edge);
                }
            }
        }
        previous = Some(e);
    }
    assert_eq!(edges.len(), 24);
    assert!(edges.values().all(|seen| *seen == expected_edges));
    assert_eq!(task_degree_region.len(), 24 * 2 * 7 * 5);
}
