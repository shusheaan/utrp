//! Game harmony stays mode-relative even though capsules use major-key memory.
use std::collections::{BTreeMap, BTreeSet};
use utrp::{
    config::{Config, ModulationMethod, Templates},
    progression::Progression,
    theory::key::Mode,
};

#[test]
fn seventh_cycle_interprets_every_degree_in_the_actual_mode() {
    for mode in [Mode::Ionian, Mode::Aeolian] {
        let mut config = Config::load(None).unwrap().simulation;
        config.keys = vec!["C".into()];
        config.modes = vec![mode];
        config.minor_dominant_probability = 0.0;
        let templates = Templates::load(None).unwrap();
        let cycle = templates.cycle.clone();
        let mut p = Progression::new(config, templates, 6).unwrap();
        p.enable_seventh_practice(4).unwrap();
        p.configure_practice(0.0, false).unwrap();
        let mut seen = BTreeSet::new();
        for _ in 0..cycle.len() * 2 {
            let e = p.next_event();
            let degree = e.degree.unwrap();
            assert_eq!(e.key.mode, mode);
            assert_eq!(degree, cycle[e.cycle.as_ref().unwrap().step - 1]);
            assert_eq!(e.chord, e.key.chord(degree, true));
            seen.insert(degree);
            p.acknowledge_practice(&e, true);
        }
        assert_eq!(seen.len(), 7);
    }
}

#[test]
fn every_modulation_method_crosses_both_modes_after_coverage() {
    for method in [
        ModulationMethod::Dominant,
        ModulationMethod::SharedChord,
        ModulationMethod::Diminished,
    ] {
        let mut config = Config::load(None).unwrap().simulation;
        config.modulation_methods = vec![method];
        config.modulation_return_probability = 0.0;
        let mut p = Progression::new(config, Templates::load(None).unwrap(), 20261023).unwrap();
        p.enable_seventh_practice(4).unwrap();
        p.configure_practice(1.0, false).unwrap();
        let mut previous = None;
        let mut coverage = 0u8;
        let mut directions = BTreeMap::new();
        let mut roles = BTreeSet::new();
        for _ in 0..4800 {
            let e = p.next_event();
            assert_eq!(e.chord.tones.len(), 4);
            if let Some(old) = &previous {
                if old != &e.key {
                    assert_eq!(coverage, 127, "mode changes cannot bypass coverage");
                    coverage = 0;
                    assert_eq!(e.previous_key.as_ref(), Some(old));
                    *directions.entry((old.mode, e.key.mode)).or_insert(0) += 1;
                }
            }
            if e.cycle.is_some() {
                coverage |= 1 << (e.degree.unwrap() - 1);
            }
            if matches!(e.role.as_str(), "arrival" | "mode_change") {
                assert_eq!(e.chord, e.key.chord(1, true));
            }
            roles.insert(e.role.clone());
            previous = Some(e.key.clone());
            p.acknowledge_practice(&e, true);
        }
        for old in [Mode::Ionian, Mode::Aeolian] {
            for new in [Mode::Ionian, Mode::Aeolian] {
                assert!(
                    directions.get(&(old, new)).is_some_and(|n| *n > 0),
                    "{method:?}: {old:?} -> {new:?}"
                );
            }
        }
        assert!(roles.contains(match method {
            ModulationMethod::Dominant => "bridge",
            ModulationMethod::SharedChord => "shared_pivot",
            ModulationMethod::Diminished => "diminished_pivot",
        }));
        println!("{method:?}: 4800 sevenths; actual transitions {directions:?}");
    }
}
