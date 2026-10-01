use std::collections::{BTreeMap, BTreeSet};
use utrp::{
    arpeggio,
    config::Config,
    guitar::{self, GuitarPlanner},
    progression::ChordEvent,
    theory::{
        key::{Key, Mode},
        tone::Tone,
    },
};

fn event(key: &Key, degree: u8, seventh: bool, phrase: usize) -> ChordEvent {
    ChordEvent {
        id: phrase,
        phrase,
        key: key.clone(),
        chord: key.chord(degree, seventh),
        degree: Some(degree),
        role: "diatonic".into(),
        reason: String::new(),
        previous_key: None,
        cycle: None,
    }
}

#[test]
fn configurable_dwell_rotates_each_enabled_task_without_locking() {
    for every in [0, 1, 2, 3, 5, 10] {
        for stay in [1, 2, 3, 7] {
            let mut cfg = Config::load(None).unwrap().guitar;
            cfg.arpeggio_every = every;
            cfg.phrases_per_region = stay;
            let regions = cfg.regions.clone();
            let key = Key {
                tonic: Tone::parse("C").unwrap(),
                mode: Mode::Ionian,
            };
            let mut planner = GuitarPlanner::new(cfg);
            let mut counts = BTreeMap::<String, usize>::new();
            let mut observed = BTreeSet::new();
            for phrase in 0..every.max(1) * stay * regions.len() * 2 {
                let e = event(&key, 1, true, phrase);
                let first = planner.target(&e);
                let second = planner.target(&e);
                assert_eq!(
                    (first.task.clone(), first.region),
                    (second.task, second.region)
                );
                let ordinal = counts.entry(first.task.clone()).or_default();
                assert_eq!(first.region, regions[(*ordinal / stay) % regions.len()]);
                *ordinal += 1;
                observed.insert((first.task, first.region));
            }
            let tasks = if every <= 1 { 1 } else { 2 };
            assert_eq!(observed.len(), tasks * regions.len());
        }
    }
}

#[test]
fn every_concrete_configured_grip_is_selected_not_only_nearest_representative() {
    let config = Config::load(None).unwrap();
    for tonic in &config.simulation.keys {
        for mode in &config.simulation.modes {
            let key = Key {
                tonic: Tone::parse(tonic).unwrap(),
                mode: *mode,
            };
            for degree in 1..=7 {
                for seventh in [false, true] {
                    let e = event(&key, degree, seventh, 0);
                    for region in &config.guitar.regions {
                        let mut cfg = config.guitar.clone();
                        cfg.regions = vec![*region];
                        cfg.arpeggio_every = 0;
                        let shapes = guitar::shapes(&e.chord, &cfg, *region);
                        let signature = |positions: &[guitar::Position]| {
                            positions
                                .iter()
                                .map(|p| (p.string, p.fret))
                                .collect::<Vec<_>>()
                        };
                        let expected: BTreeSet<_> =
                            shapes.iter().map(|s| signature(&s.positions)).collect();
                        let mut sizes = BTreeMap::new();
                        for shape in &shapes {
                            *sizes
                                .entry((
                                    shape.positions.iter().map(|p| p.string).collect::<Vec<_>>(),
                                    shape.inversion,
                                ))
                                .or_insert(0) += 1;
                        }
                        let bound = sizes.len() * sizes.values().max().copied().unwrap_or(0);
                        let mut planner = GuitarPlanner::new(cfg);
                        let observed: BTreeSet<_> = (0..bound)
                            .map(|_| signature(&planner.target(&e).shape.unwrap().positions))
                            .collect();
                        assert_eq!(
                            observed,
                            expected,
                            "{} degree {degree}, region {region:?}",
                            key.label()
                        );
                    }
                }
            }
        }
    }
}

#[test]
fn detached_exploration_exhausts_finite_cyclic_position_products() {
    let config = Config::load(None).unwrap();
    let cfg = config.guitar;
    for tonic in &config.simulation.keys {
        for mode in [Mode::Ionian, Mode::Aeolian] {
            let key = Key {
                tonic: Tone::parse(tonic).unwrap(),
                mode,
            };
            for degree in 1..=7 {
                for seventh in [false, true] {
                    let chord = key.chord(degree, seventh);
                    for region in &cfg.regions {
                        let available: Vec<BTreeSet<(u8, u8)>> = chord
                            .tones
                            .iter()
                            .map(|tone| {
                                (1..=6)
                                    .flat_map(|s| (region[0]..=region[1]).map(move |f| (s, f)))
                                    .filter(|(s, f)| {
                                        (cfg.tuning[usize::from(6 - s)] + f) % 12 == tone.pc
                                    })
                                    .collect()
                            })
                            .collect();
                        let count = chord.tones.len()
                            * available.iter().map(BTreeSet::len).product::<usize>();
                        let mut seen = BTreeSet::new();
                        for ordinal in 0..count {
                            let path = arpeggio::path(&chord, &cfg, *region, ordinal * 2);
                            assert_eq!(path.len(), chord.tones.len());
                            for (step, p) in path.iter().enumerate() {
                                let member =
                                    (ordinal % chord.tones.len() + step) % chord.tones.len();
                                assert!(available[member].contains(&(p.string, p.fret)));
                                assert_eq!(p.midi, cfg.tuning[usize::from(6 - p.string)] + p.fret);
                                assert_eq!(p.degree, chord.degrees[member]);
                                assert_eq!(p.finger, None);
                            }
                            seen.insert(
                                path.iter().map(|p| (p.string, p.fret)).collect::<Vec<_>>(),
                            );
                        }
                        assert_eq!(seen.len(), count, "{} {region:?}", chord.symbol());
                        assert_eq!(
                            arpeggio::path(&chord, &cfg, *region, 0),
                            arpeggio::path(&chord, &cfg, *region, count * 2)
                        );
                    }
                }
            }
        }
    }
}
