use std::collections::BTreeSet;
use utrp::{
    config::{Config, Templates},
    progression::{ChordEvent, Progression},
    session::{Action, Session},
    simulator,
    theory::{
        chord::Chord,
        key::{Key, Mode},
        tone::Tone,
    },
};

fn engine(config: &Config, seed: u64) -> Progression {
    Progression::new(
        config.simulation.clone(),
        Templates::load(None).unwrap(),
        seed,
    )
    .unwrap()
}

fn forced(substitute: bool) -> Config {
    let mut c = Config::load(None).unwrap();
    c.simulation.secondary_probability = 0.0;
    c.simulation.substitution_probability = 0.0;
    c.simulation.borrow_probability = 0.0;
    c.simulation.sd25_probability = if substitute { 0.0 } else { 1.0 };
    c.simulation.ssd25_probability = if substitute { 1.0 } else { 0.0 };
    c
}

#[test]
fn ii_v_spelling_and_quality_follow_target_not_global_mode() {
    for (tonic, mode, sd, ssd) in [
        ("C", Mode::Ionian, ["Dm7", "G7"], ["Abm7", "Db7"]),
        ("A", Mode::Aeolian, ["Bm7b5", "E7"], ["Fm7", "Bb7"]),
        ("F#", Mode::Aeolian, ["G#m7b5", "C#7"], ["Dm7", "G7"]),
        ("Db", Mode::Ionian, ["Ebm7", "Ab7"], ["Bbbm7", "Ebb7"]),
    ] {
        let target = Key {
            tonic: Tone::parse(tonic).unwrap(),
            mode,
        }
        .chord(1, false);
        for (substitute, expected) in [(false, sd), (true, ssd)] {
            let chain = target.approach_ii_v(substitute).unwrap();
            assert_eq!(chain.map(|c| c.symbol()), expected);
        }
    }
    let config = Config::load(None).unwrap();
    for tonic in &config.simulation.keys {
        for mode in &config.simulation.modes {
            let key = Key {
                tonic: Tone::parse(tonic).unwrap(),
                mode: *mode,
            };
            for degree in 1..=7 {
                for seventh in [false, true] {
                    let target = key.chord(degree, seventh);
                    for sub in [false, true] {
                        let Some([ii, v]) = target.approach_ii_v(sub) else {
                            assert!(matches!(target.quality.as_str(), "dim" | "m7b5"));
                            continue;
                        };
                        let minor = matches!(target.quality.as_str(), "m" | "m7");
                        assert_eq!(ii.quality, if minor && !sub { "m7b5" } else { "m7" });
                        assert_eq!(v.quality, "7");
                        assert_eq!(
                            (v.root.pc + 12 - target.root.pc) % 12,
                            if sub { 1 } else { 7 }
                        );
                        assert_eq!(
                            (ii.root.pc + 12 - target.root.pc) % 12,
                            if sub { 8 } else { 2 }
                        );
                        for c in [ii, v] {
                            assert_eq!(c.degrees, [1, 3, 5, 7]);
                            assert_eq!(c.pcs().into_iter().collect::<BTreeSet<_>>().len(), 4);
                        }
                    }
                }
            }
        }
    }
    for intervals in [vec![(0, 0), (4, 2), (8, 4)], vec![(0, 0), (2, 1), (7, 4)]] {
        let root = Tone::parse("C").unwrap();
        let chord = Chord::from_tones(
            intervals
                .into_iter()
                .map(|(n, d)| root.transpose(n, d))
                .collect(),
            vec![1, 3, 5],
        );
        assert!(chord.approach_ii_v(false).is_none());
        assert!(chord.approach_ii_v(true).is_none());
    }
}

fn check_chain(ii: &ChordEvent, v: &ChordEvent, target: &ChordEvent, substitute: bool) {
    assert_eq!(v.role, if substitute { "ssd25_v" } else { "sd25_v" });
    assert_eq!(target.role, "diatonic");
    assert_eq!(ii.key, target.key);
    assert_eq!(v.key, target.key);
    assert_eq!(ii.phrase, target.phrase);
    assert_eq!(v.phrase, target.phrase);
    assert!(ii.previous_key.is_none() && v.previous_key.is_none());
    assert!(ii.cycle.is_none() && v.cycle.is_none());
    assert_eq!(
        target.chord.approach_ii_v(substitute).unwrap(),
        [ii.chord.clone(), v.chord.clone()]
    );
    assert_eq!(ii.reason, v.reason);
    assert!(ii.reason.contains(&target.chord.symbol()));
}

#[test]
fn chains_are_atomic_and_preserve_every_backbone_step_across_chunks_and_modulations() {
    for sub in [false, true] {
        for chunk in 1..=8 {
            let mut config = forced(sub);
            config.simulation.cycle_chunk_size = chunk;
            config.simulation.modulation_probability = 1.0;
            let mut p = engine(&config, 42);
            let rows: Vec<_> = (0..4000).map(|_| p.next_event()).collect();
            assert_eq!(rows[0].role, "diatonic");
            let mut chains = 0;
            for group in rows.windows(3) {
                if group[0].role == if sub { "ssd25_ii" } else { "sd25_ii" } {
                    check_chain(&group[0], &group[1], &group[2], sub);
                    chains += 1;
                }
            }
            assert!(chains > 500);
            let mut previous: Option<&ChordEvent> = None;
            for row in rows.iter().filter(|row| row.cycle.is_some()) {
                let step = row.cycle.as_ref().unwrap().step;
                if let Some(old) = previous {
                    let old_step = old.cycle.as_ref().unwrap().step;
                    if old.key != row.key {
                        assert_eq!((old_step, step), (40, 1));
                    } else {
                        assert_eq!(step, if old_step == 40 { 2 } else { old_step + 1 });
                    }
                }
                previous = Some(row);
            }
            for pair in rows.windows(2) {
                if pair[0].role == "minor_dominant" {
                    assert_eq!(pair[1].degree, Some(1));
                    assert_eq!(pair[1].role, "diatonic");
                }
                if pair[0].role == "bridge" {
                    assert!(matches!(pair[1].role.as_str(), "arrival" | "mode_change"));
                }
                if pair[0].key != pair[1].key {
                    assert_eq!(pair[0].cycle.as_ref().unwrap().step, 40);
                }
            }
        }
    }
}

#[test]
fn defaults_emit_all_approaches_without_ambient_or_borrowing_and_can_disable_them() {
    let mut config = Config::load(None).unwrap();
    let mut p = engine(&config, 7);
    let mut roles = BTreeSet::new();
    for _ in 0..10000 {
        let e = p.next_event();
        assert!(matches!(e.chord.tones.len(), 3 | 4));
        roles.insert(e.role);
    }
    for role in [
        "secondary",
        "substitute",
        "sd25_ii",
        "sd25_v",
        "ssd25_ii",
        "ssd25_v",
    ] {
        assert!(roles.contains(role));
    }
    assert!(!roles.contains("borrowed"));
    config.simulation.approaches = false;
    let mut p = engine(&config, 7);
    assert!((0..2000).all(|_| !matches!(
        p.next_event().role.as_str(),
        "secondary" | "substitute" | "sd25_ii" | "sd25_v" | "ssd25_ii" | "ssd25_v"
    )));
}

#[test]
fn approach_parameters_are_validated_at_config_and_generator_boundaries() {
    for value in [-0.1, 1.1, f64::NAN, f64::INFINITY] {
        for sub in [false, true] {
            let mut c = forced(sub);
            if sub {
                c.simulation.ssd25_probability = value;
            } else {
                c.simulation.sd25_probability = value;
            }
            assert!(c.validate().is_err());
            assert!(Progression::new(c.simulation, Templates::load(None).unwrap(), 42).is_err());
        }
    }
    let mut c = forced(false);
    c.simulation.ssd25_probability = 0.1;
    assert!(c.validate().is_err());
    let legacy = Config::load(Some(std::path::Path::new(
        "tests/fixtures/legacy-seven-mode.toml",
    )))
    .unwrap();
    assert!(!legacy.simulation.approaches);
    assert_eq!(legacy.simulation.sd25_probability, 0.0);
    assert_eq!(legacy.simulation.ssd25_probability, 0.0);
}

#[test]
fn major_v7_resolution_is_not_interrupted_across_preview_chunks() {
    let mut c = forced(true);
    c.simulation.keys = vec!["C".into()];
    c.simulation.modes = vec![Mode::Ionian];
    c.simulation.seventh_probability = 1.0;
    c.simulation.cycle_chunk_size = 1;
    let mut p = engine(&c, 42);
    let mut count = 0;
    let cycle = Templates::load(None).unwrap().cycle;
    for _ in 0..1000 {
        let e = p.next_event();
        if let Some(pos) = &e.cycle {
            if e.degree == Some(5) && cycle.get(pos.step) == Some(&1) {
                assert_eq!(e.chord.symbol(), "G7");
                let next = p.next_event();
                assert_eq!(next.chord.symbol(), "Cmaj7");
                assert_eq!(next.role, "diatonic");
                count += 1;
            }
        }
    }
    assert!(count > 5);
}

#[test]
fn inserted_targets_use_real_guitar_paths_and_normal_scoring() {
    let c = Config::load(None).unwrap();
    let mut stream = simulator::stream(&c, Templates::load(None).unwrap(), 42, 48).unwrap();
    let mut seen = BTreeSet::new();
    for _ in 0..30000 {
        let target = stream.next_target();
        if !target.music.role.starts_with("sd25_") && !target.music.role.starts_with("ssd25_") {
            continue;
        }
        let positions = if target.guitar.task == "chord" {
            &target
                .guitar
                .shape
                .as_ref()
                .expect("playable grip")
                .positions
        } else {
            &target.guitar.arpeggio
        };
        let pcs: BTreeSet<_> = positions.iter().map(|p| p.midi % 12).collect();
        assert_eq!(pcs, target.music.chord.pcs().into_iter().collect());
        for p in positions {
            assert_eq!(p.midi, c.guitar.tuning[usize::from(6 - p.string)] + p.fret);
        }
        seen.insert((target.music.role, target.guitar.task, target.guitar.region));
    }
    assert_eq!(seen.len(), 4 * 2 * 5);
    let c = forced(false);
    let stream = simulator::stream(&c, Templates::load(None).unwrap(), 42, 48).unwrap();
    let mut s = Session::new(stream, c.session, 0);
    while s.target().music.role != "sd25_ii" {
        let id = s.target().music.id;
        s.apply(Action::Next, 0, id);
    }
    let original = s.target().clone();
    for _ in 0..3 {
        let id = s.target().music.id;
        s.apply(Action::Confirm, 1, id);
    }
    assert_eq!(s.summary(1).confirmed, 3);
    let amount = s.key_practice().clone();
    for _ in 0..3 {
        let id = s.target().music.id;
        s.apply(Action::Previous, 2, id);
    }
    assert_eq!(s.target(), &original);
    assert_eq!(s.key_practice(), &amount);
    let id = s.target().music.id;
    s.apply(Action::Confirm, 3, id);
    assert_eq!(s.summary(3).confirmed, 3);
}
