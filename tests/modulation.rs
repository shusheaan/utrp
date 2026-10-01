use std::collections::BTreeSet;
use utrp::{
    config::{Config, ModulationMethod, Templates},
    modulation::{available_methods, diminished_pivot, leading_diminished, shared_chords},
    progression::{ChordEvent, Progression},
    simulator,
    theory::{
        key::{Key, Mode},
        tone::Tone,
    },
};

fn key(name: &str, mode: Mode) -> Key {
    Key {
        tonic: Tone::parse(name).unwrap(),
        mode,
    }
}
fn events(config: &Config, seed: u64, count: usize) -> Vec<ChordEvent> {
    let mut engine = Progression::new(
        config.simulation.clone(),
        Templates::load(None).unwrap(),
        seed,
    )
    .unwrap();
    (0..count).map(|_| engine.next_event()).collect()
}
fn config(method: ModulationMethod) -> Config {
    let mut config = Config::load(None).unwrap();
    config.simulation.modulation_probability = 1.0;
    config.simulation.modulation_return_probability = 0.0;
    config.simulation.modulation_methods = vec![method];
    config
}

#[test]
fn common_chords_match_complete_members_and_both_degrees_for_all_key_pairs() {
    let config = Config::load(None).unwrap();
    let keys: Vec<_> = config
        .simulation
        .keys
        .iter()
        .flat_map(|n| [Mode::Ionian, Mode::Aeolian].map(|m| key(n, m)))
        .collect();
    for old in &keys {
        for new in &keys {
            let pivots = shared_chords(old, new);
            for seventh in [false, true] {
                for degree in 1..=7 {
                    let chord = old.chord(degree, seventh);
                    let expected = (1..=7).any(|d| {
                        let c = new.chord(d, seventh);
                        c.root.pc == chord.root.pc && c.pcs() == chord.pcs()
                    });
                    assert_eq!(
                        pivots.iter().any(|p| p.old_degree == degree
                            && p.chord == new.chord(p.new_degree, seventh)),
                        expected
                    );
                }
            }
            for pivot in pivots {
                assert_eq!(
                    old.chord(pivot.old_degree, pivot.chord.tones.len() == 4)
                        .pcs(),
                    pivot.chord.pcs()
                );
            }
        }
    }
    // G triad is shared by C and D major; Gmaj7 is NOT (F versus F#).
    let pivots = shared_chords(&key("C", Mode::Ionian), &key("D", Mode::Ionian));
    assert!(pivots.iter().any(|p| p.chord.symbol() == "G"));
    assert!(!pivots.iter().any(|p| p.chord.symbol() == "Gmaj7"));
}

#[test]
fn diminished_reinterpretation_preserves_all_four_pitches_and_correct_spelling() {
    let c = key("C", Mode::Ionian);
    let eb = key("Eb", Mode::Aeolian);
    let source = leading_diminished(&c);
    let target = leading_diminished(&eb);
    assert_eq!(
        source
            .tones
            .iter()
            .map(|n| n.name.as_str())
            .collect::<Vec<_>>(),
        ["B", "D", "F", "Ab"]
    );
    assert_eq!(
        target
            .tones
            .iter()
            .map(|n| n.name.as_str())
            .collect::<Vec<_>>(),
        ["D", "F", "Ab", "Cb"]
    );
    assert_eq!(target.degree_label(3), "bb7");
    assert!(diminished_pivot(&c, &eb));
    assert!(!diminished_pivot(&c, &key("D", Mode::Ionian)));
    assert!(!diminished_pivot(&c, &key("C", Mode::Aeolian)));
    for name in &Config::load(None).unwrap().simulation.keys {
        for mode in [Mode::Ionian, Mode::Aeolian] {
            let destination = key(name, mode);
            let interval = destination.tonic.pc;
            assert_eq!(
                diminished_pivot(&c, &destination),
                matches!(interval, 3 | 6 | 9)
            );
        }
    }
}

#[test]
fn each_migrated_route_is_used_and_resolves_before_resuming_the_cycle() {
    for (method, role) in [
        (ModulationMethod::SharedChord, "shared_pivot"),
        (ModulationMethod::Diminished, "diminished_pivot"),
    ] {
        let config = config(method);
        let output = events(&config, 42, 4000);
        let mut count = 0;
        for window in output.windows(4) {
            let [closing, pivot, dominant, arrival] = window else {
                unreachable!()
            };
            if pivot.role != role {
                continue;
            }
            count += 1;
            assert_eq!(closing.cycle.as_ref().unwrap().step, 40);
            assert_eq!(pivot.previous_key.as_ref(), Some(&closing.key));
            assert_ne!(pivot.key, closing.key);
            assert_eq!(dominant.role, "bridge");
            assert_eq!(dominant.chord.quality, "7");
            assert_eq!(dominant.key, pivot.key);
            assert_eq!(dominant.chord, pivot.key.chord(1, false).secondary());
            assert_eq!(arrival.chord, pivot.key.chord(1, false));
            assert_eq!(arrival.cycle.as_ref().unwrap().step, 1);
            if method == ModulationMethod::SharedChord {
                assert!(shared_chords(&closing.key, &pivot.key)
                    .iter()
                    .any(|p| p.chord == pivot.chord && Some(p.new_degree) == pivot.degree));
            } else {
                assert!(diminished_pivot(&closing.key, &pivot.key));
                assert_eq!(pivot.chord, leading_diminished(&pivot.key));
            }
        }
        assert!(count > 50, "route not exercised: {role}");
    }
}

#[test]
fn unreachable_method_pool_stays_put_without_fake_pivots() {
    for method in [ModulationMethod::SharedChord, ModulationMethod::Diminished] {
        let mut config = config(method);
        config.simulation.keys = vec!["C".into(), "Db".into()];
        config.simulation.modes = vec![Mode::Ionian];
        let output = events(&config, 42, 200);
        assert!(output
            .iter()
            .all(|e| e.key == output[0].key && e.previous_key.is_none()));
        assert!(output
            .iter()
            .any(|e| e.reason.starts_with("No supported modulation path")));
    }
}

#[test]
fn all_routes_default_cover_24_keys_and_return_does_not_trap_exploration() {
    for probability in [0.0, 0.2, 1.0] {
        let mut config = Config::load(None).unwrap();
        config.simulation.modulation_probability = 1.0;
        config.simulation.modulation_return_probability = probability;
        for seed in [7, 42, 20261001] {
            let output = events(&config, seed, 6000);
            assert_eq!(
                output
                    .iter()
                    .map(|e| e.key.label())
                    .collect::<BTreeSet<_>>()
                    .len(),
                24
            );
            for role in ["shared_pivot", "diminished_pivot", "bridge"] {
                assert!(
                    output.iter().any(|e| e.role == role),
                    "missing {role}, seed {seed}"
                );
            }
        }
    }
}

#[test]
fn forced_return_goes_to_previous_key_not_permanent_start_and_has_a_bridge() {
    let mut config = Config::load(None).unwrap();
    // Isolate Back semantics here; key_balance tests exercise its fairness guard.
    config.simulation.key_balance_tolerance = 100_000;
    config.simulation.modulation_probability = 1.0;
    config.simulation.modulation_return_probability = 1.0;
    let output = events(&config, 7, 5000);
    let mut visits = vec![output[0].key.clone()];
    let mut returns = 0;
    for e in output.iter().filter(|e| e.role == "bridge") {
        if e.reason.starts_with("Return: ") {
            returns += 1;
            assert_eq!(e.key, visits[visits.len() - 2]);
            assert_eq!(e.previous_key.as_ref(), visits.last());
        }
        visits.push(e.key.clone());
    }
    assert!(returns > 30);
    assert_eq!(visits[0], visits[2]);
    assert_ne!(visits[1], visits[3]); // return is followed by exploration, not endless A-B-A-B
                                      // With forced excursions the starting key naturally remains the anchor.
                                      // Allow intervening exploration to prove Back follows the latest key instead.
    config.simulation.modulation_return_probability = 0.5;
    let output = events(&config, 7, 5000);
    let mut visits = vec![output[0].key.clone()];
    let mut non_initial = false;
    for e in output.iter().filter(|e| e.role == "bridge") {
        if e.reason.starts_with("Return: ") {
            assert_eq!(e.key, visits[visits.len() - 2]);
            non_initial |= e.key != visits[0];
        }
        visits.push(e.key.clone());
    }
    assert!(non_initial);
}

#[test]
fn invalid_route_config_rejected_and_legacy_config_preserved() {
    let mut config = Config::load(None).unwrap();
    config.simulation.modulation_methods.clear();
    assert!(config.validate().is_err());
    assert!(
        Progression::new(config.simulation.clone(), Templates::load(None).unwrap(), 0).is_err()
    );
    config.simulation.modulation_methods = vec![ModulationMethod::Dominant; 2];
    assert!(config.validate().is_err());
    config.simulation.modulation_methods = vec![ModulationMethod::Dominant];
    for p in [-0.1, 1.1, f64::NAN, f64::INFINITY] {
        config.simulation.modulation_return_probability = p;
        assert!(config.validate().is_err());
        assert!(
            Progression::new(config.simulation.clone(), Templates::load(None).unwrap(), 0).is_err()
        );
    }
    let legacy = Config::load(Some(std::path::Path::new(
        "tests/fixtures/legacy-seven-mode.toml",
    )))
    .unwrap();
    assert_eq!(
        legacy.simulation.modulation_methods,
        [ModulationMethod::Dominant]
    );
    assert_eq!(legacy.simulation.modulation_return_probability, 0.0);
    assert!(available_methods(
        &key("C", Mode::Ionian),
        &key("G", Mode::Dorian),
        &[ModulationMethod::Diminished]
    )
    .is_empty());
}

#[test]
fn migrated_pivots_have_playable_guitar_targets_and_complete_detached_paths() {
    let mut config = Config::load(None).unwrap();
    config.simulation.modulation_probability = 1.0;
    let mut seen = BTreeSet::new();
    for seed in [7, 42, 20261001] {
        let mut stream =
            simulator::stream(&config, Templates::load(None).unwrap(), seed, 48).unwrap();
        // Approach insertions lengthen each cycle; keep enough modulation
        // opportunities to cover every pivot/task/region combination.
        for _ in 0..30000 {
            let t = stream.next_target();
            if !matches!(t.music.role.as_str(), "shared_pivot" | "diminished_pivot") {
                continue;
            }
            seen.insert((t.music.role.clone(), t.guitar.task.clone(), t.guitar.region));
            let positions = if t.guitar.task == "chord" {
                &t.guitar
                    .shape
                    .as_ref()
                    .expect("playable bridge grip")
                    .positions
            } else {
                &t.guitar.arpeggio
            };
            assert_eq!(positions.len(), t.music.chord.tones.len());
            assert_eq!(
                positions
                    .iter()
                    .map(|p| p.midi % 12)
                    .collect::<BTreeSet<_>>(),
                t.music.chord.pcs().into_iter().collect()
            );
            for p in positions {
                assert_eq!(
                    p.midi,
                    config.guitar.tuning[usize::from(6 - p.string)] + p.fret
                );
            }
        }
    }
    assert_eq!(seen.len(), 2 * 2 * 5); // both routes, both tasks, all five regions
}
