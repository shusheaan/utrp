//! Slow, deterministic coverage audit. Not a proof of covering every possible voicing.
//! Run: cargo test --release --test coverage -- --ignored --nocapture
use serde::Serialize;
use serde_json::{json, Value};
use std::{
    collections::{BTreeMap, BTreeSet},
    fs,
    path::Path,
    time::Instant,
};
use utrp::{
    config::{Config, Guitar, Templates},
    guitar::Position,
    session::Target,
    simulator,
    theory::{chord::Chord, key::Key, tone::Tone},
};

const OUTPUT: &str = "target/coverage";
const SEED: u64 = 20260930;

fn bump(map: &mut BTreeMap<String, usize>, label: String) {
    *map.entry(label).or_default() += 1;
}
fn base_label(key: &Key, degree: u8, seventh: bool) -> String {
    format!(
        "{}|degree={degree}|{}",
        key.label(),
        if seventh { "seventh" } else { "triad" }
    )
}
fn grip_label(base: &str, region: [u8; 2], strings: &[u8], inversion: usize) -> String {
    format!("{base}|region={region:?}|strings={strings:?}|inversion={inversion}")
}

#[derive(Default, Serialize)]
struct Expected {
    basics: BTreeSet<String>,
    feasible_grips: BTreeSet<String>,
    physical_grips: BTreeSet<String>,
    structurally_inapplicable_grips: BTreeSet<String>,
}

// Independent finite fret-product oracle: does NOT call guitar::shapes/planner.
// Matches the documented configured model, not human ergonomic certification.
fn feasible_inversions(
    chord: &Chord,
    cfg: &Guitar,
    region: [u8; 2],
    strings: &[u8],
) -> (BTreeSet<usize>, BTreeSet<Vec<(u8, u8)>>) {
    let width = usize::from(region[1] - region[0] + 1);
    let mut inversions = BTreeSet::new();
    let mut physical = BTreeSet::new();
    for encoded in 0..width.pow(strings.len() as u32) {
        let mut remainder = encoded;
        let mut notes = Vec::new();
        let mut frets = Vec::new();
        for string in strings {
            let fret = region[0] + (remainder % width) as u8;
            remainder /= width;
            frets.push(fret);
            notes.push(cfg.tuning[usize::from(6 - string)] + fret);
        }
        if !notes.windows(2).all(|pair| pair[0] < pair[1]) {
            continue;
        }
        let pcs: BTreeSet<_> = notes.iter().map(|note| note % 12).collect();
        if pcs != chord.pcs().into_iter().collect() || pcs.len() != notes.len() {
            continue;
        }
        let stopped: Vec<_> = frets.iter().copied().filter(|fret| *fret > 0).collect();
        if let Some(low) = stopped.iter().min() {
            if stopped.iter().max().unwrap() - low > cfg.max_span {
                continue;
            }
            let barred: Vec<_> = strings
                .iter()
                .zip(&frets)
                .filter(|(_, f)| *f == low)
                .map(|(s, _)| *s)
                .collect();
            if barred.len() > 1 {
                let first = *barred.iter().min().unwrap();
                let last = *barred.iter().max().unwrap();
                if strings
                    .iter()
                    .zip(&frets)
                    .any(|(s, f)| first <= *s && *s <= last && f < low)
                {
                    continue;
                }
            }
            if 1 + stopped.iter().filter(|f| *f > low).count() > 4 {
                continue;
            }
        }
        physical.insert(strings.iter().copied().zip(frets.iter().copied()).collect());
        inversions.insert(
            chord
                .tones
                .iter()
                .position(|tone| tone.pc == notes[0] % 12)
                .unwrap(),
        );
    }
    (inversions, physical)
}

fn expected(config: &Config) -> Expected {
    let mut result = Expected::default();
    for tonic in &config.simulation.keys {
        for mode in &config.simulation.modes {
            let key = Key {
                tonic: Tone::parse(tonic).unwrap(),
                mode: *mode,
            };
            for degree in 1..=7 {
                for seventh in [false, true] {
                    let chord = key.chord(degree, seventh);
                    let base = base_label(&key, degree, seventh);
                    result.basics.insert(base.clone());
                    let sets = if seventh {
                        &config.guitar.seventh_strings
                    } else {
                        &config.guitar.triad_strings
                    };
                    for region in &config.guitar.regions {
                        for strings in sets {
                            let (feasible, physical) =
                                feasible_inversions(&chord, &config.guitar, *region, strings);
                            for positions in physical {
                                result
                                    .physical_grips
                                    .insert(format!("{base}|{region:?}|{positions:?}"));
                            }
                            for inversion in 0..chord.tones.len() {
                                let label = grip_label(&base, *region, strings, inversion);
                                if feasible.contains(&inversion) {
                                    result.feasible_grips.insert(label);
                                } else {
                                    result.structurally_inapplicable_grips.insert(label);
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    result
}

#[derive(Default, Serialize)]
struct TaskStats {
    events: usize,
    regions: BTreeMap<String, usize>,
    root_strings: BTreeMap<String, usize>,
    lowest_pitch_members: BTreeMap<String, usize>,
    starting_members: BTreeMap<String, usize>,
    string_sets_or_ordered_paths: BTreeMap<String, usize>,
    qualities: BTreeMap<String, usize>,
    families: BTreeMap<String, usize>,
    lowest_members_by_quality: BTreeMap<String, usize>,
    strings_by_member_count: BTreeMap<String, usize>,
    basics: BTreeSet<String>,
}
#[derive(Default, Serialize)]
struct Observed {
    events: usize,
    grip_presentations: BTreeMap<String, usize>,
    key_modes: BTreeMap<String, usize>,
    roles: BTreeMap<String, usize>,
    ambient_colors: BTreeMap<String, usize>,
    tasks: BTreeMap<String, TaskStats>,
    basics: BTreeSet<String>,
    chord_grips: BTreeSet<String>,
    physical_grips: BTreeSet<String>,
    no_chord_shape: usize,
    incomplete_arpeggio: usize,
    unusable_examples: Vec<Value>,
    milestones: Vec<Value>,
    first_full_coverage_at_event: BTreeMap<String, usize>,
}

fn validate_positions(positions: &[Position], chord: &Chord, config: &Config, region: [u8; 2]) {
    for position in positions {
        assert!((1..=6).contains(&position.string));
        assert!((region[0]..=region[1]).contains(&position.fret));
        assert_eq!(
            position.midi,
            config.guitar.tuning[usize::from(6 - position.string)] + position.fret
        );
        assert!(chord.pcs().contains(&(position.midi % 12)));
    }
    let pcs: BTreeSet<_> = positions.iter().map(|p| p.midi % 12).collect();
    assert_eq!(positions.len(), chord.tones.len());
    assert_eq!(pcs, chord.pcs().into_iter().collect());
}

fn observe_positions(stats: &mut TaskStats, positions: &[Position], chord: &Chord) {
    for p in positions.iter().filter(|p| p.midi % 12 == chord.root.pc) {
        bump(&mut stats.root_strings, p.string.to_string());
    }
    let member = |p: &Position| {
        chord
            .tones
            .iter()
            .position(|tone| tone.pc == p.midi % 12)
            .unwrap()
            .to_string()
    };
    if let Some(lowest) = positions.iter().min_by_key(|p| p.midi) {
        bump(&mut stats.lowest_pitch_members, member(lowest));
        bump(
            &mut stats.lowest_members_by_quality,
            format!(
                "quality={}|members={}|lowest_member={}",
                chord.quality,
                chord.tones.len(),
                member(lowest)
            ),
        );
    }
    if let Some(first) = positions.first() {
        bump(&mut stats.starting_members, member(first));
    }
    bump(
        &mut stats.strings_by_member_count,
        format!(
            "members={}|strings={:?}",
            chord.tones.len(),
            positions.iter().map(|p| p.string).collect::<Vec<_>>()
        ),
    );
    bump(
        &mut stats.string_sets_or_ordered_paths,
        format!(
            "{:?}",
            positions.iter().map(|p| p.string).collect::<Vec<_>>()
        ),
    );
}

fn observe(result: &mut Observed, target: &Target, config: &Config) {
    result.events += 1;
    let music = &target.music;
    let guitar = &target.guitar;
    bump(&mut result.key_modes, music.key.label());
    bump(&mut result.roles, music.role.clone());
    if ["sus2", "sus4", "add9", "m(add9)", "maj7(#11,no5)"].contains(&music.chord.quality.as_str())
    {
        bump(&mut result.ambient_colors, music.chord.quality.clone());
    }
    // Exact chord equality, not merely a degree/role label: colors do not count as basics.
    let base = music.degree.and_then(|degree| {
        [false, true].into_iter().find_map(|seventh| {
            (music.chord == music.key.chord(degree, seventh))
                .then(|| base_label(&music.key, degree, seventh))
        })
    });
    let stats = result.tasks.entry(guitar.task.clone()).or_default();
    stats.events += 1;
    bump(&mut stats.regions, format!("{:?}", guitar.region));
    bump(
        &mut stats.qualities,
        if music.chord.quality.is_empty() {
            "major".into()
        } else {
            music.chord.quality.clone()
        },
    );
    if let Some(base) = &base {
        result.basics.insert(base.clone());
        stats.basics.insert(base.clone());
    }
    let positions = if guitar.task == "chord" {
        if let Some(shape) = &guitar.shape {
            bump(&mut stats.families, shape.family.clone());
            if let Some(base) = base {
                let positions: Vec<_> =
                    shape.positions.iter().map(|p| (p.string, p.fret)).collect();
                result
                    .physical_grips
                    .insert(format!("{base}|{:?}|{positions:?}", guitar.region));
                let strings: Vec<_> = shape.positions.iter().map(|p| p.string).collect();
                let label = grip_label(&base, guitar.region, &strings, shape.inversion);
                bump(&mut result.grip_presentations, label.clone());
                result.chord_grips.insert(label);
            }
            assert!(shape
                .positions
                .windows(2)
                .all(|pair| pair[0].midi < pair[1].midi));
            assert_eq!(
                shape.inversion,
                music
                    .chord
                    .tones
                    .iter()
                    .position(|tone| tone.pc == shape.positions[0].midi % 12)
                    .unwrap()
            );
            &shape.positions
        } else {
            result.no_chord_shape += 1;
            if result.unusable_examples.len() < 30 {
                result.unusable_examples.push(json!(target));
            }
            return;
        }
    } else {
        assert_eq!(guitar.task, "arpeggio_detached");
        // Deliberately do NOT inspect/count the hidden simultaneous shape.
        bump(&mut stats.families, "not_applicable_detached".into());
        if guitar.arpeggio.len() != music.chord.tones.len() {
            result.incomplete_arpeggio += 1;
            if result.unusable_examples.len() < 30 {
                result.unusable_examples.push(json!(target));
            }
            return;
        }
        &guitar.arpeggio
    };
    validate_positions(positions, &music.chord, config, guitar.region);
    observe_positions(stats, positions, &music.chord);
}

fn write_json(name: &str, value: &impl Serialize) {
    let directory = std::env::var_os("UTRP_COVERAGE_DIR")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| OUTPUT.into());
    let path = directory.join(format!("coverage-{name}.json"));
    fs::create_dir_all(directory).unwrap();
    fs::write(path, serde_json::to_vec_pretty(value).unwrap()).unwrap();
}
fn run(
    label: &str,
    config: &Config,
    count: usize,
    expected: &Expected,
    seed: u64,
    stop_on_full: bool,
) -> Observed {
    let start = Instant::now();
    let mut stream = simulator::stream(config, Templates::load(None).unwrap(), seed, 48).unwrap();
    let mut result = Observed::default();
    for index in 0..count {
        let target = stream.next_target();
        assert_eq!(target.music.id, index);
        observe(&mut result, &target, config);
        for (label, actual, required) in [
            (
                "key_modes",
                result.key_modes.len(),
                config.simulation.keys.len() * config.simulation.modes.len(),
            ),
            (
                "real_basic_targets",
                result.basics.len(),
                expected.basics.len(),
            ),
            (
                "physical_grips",
                result.physical_grips.len(),
                expected.physical_grips.len(),
            ),
            (
                "feasible_chord_grips",
                result.chord_grips.len(),
                expected.feasible_grips.len(),
            ),
        ] {
            if actual == required {
                result
                    .first_full_coverage_at_event
                    .entry(label.into())
                    .or_insert(index + 1);
            }
        }
        if [10_000, 100_000, 200_000, 500_000, 1_000_000, 2_000_000].contains(&(index + 1)) {
            let milestone = json!({"events":index+1,"seconds":start.elapsed().as_secs_f64(),"key_modes":result.key_modes.len(),"basics":result.basics.len(),"feasible_chord_grips":result.chord_grips.len()});
            println!("{label}: {milestone}");
            result.milestones.push(milestone);
        }
        if stop_on_full
            && result.events >= 1_000_000
            && result.chord_grips.len() == expected.feasible_grips.len()
            && result.physical_grips == expected.physical_grips
        {
            break;
        }
    }
    let missing_basics: Vec<_> = expected.basics.difference(&result.basics).collect();
    let missing_grips: Vec<_> = expected
        .feasible_grips
        .difference(&result.chord_grips)
        .collect();
    let unexpected_grips: Vec<_> = result
        .chord_grips
        .difference(&expected.feasible_grips)
        .collect();
    let missing_physical: Vec<_> = expected
        .physical_grips
        .difference(&result.physical_grips)
        .collect();
    assert!(result.physical_grips.is_subset(&expected.physical_grips));
    let summary = json!({"physical_grips_expected":expected.physical_grips.len(),"physical_grips_observed":result.physical_grips.len(),"missing_physical_grips":missing_physical,"label":label,"seed":seed,"events":result.events,"event_limit":count,"first_full_coverage_at_event":result.first_full_coverage_at_event,"grip_presentations_distribution":presentation_distribution(&result, expected),"seconds":start.elapsed().as_secs_f64(),"key_modes":result.key_modes.len(),"basic_targets_observed":result.basics.len(),"basic_targets_expected":expected.basics.len(),"feasible_chord_grips_observed":result.chord_grips.len(),"feasible_chord_grips_expected":expected.feasible_grips.len(),"structurally_inapplicable_grips":expected.structurally_inapplicable_grips.len(),"missing_basics":missing_basics,"missing_grips":missing_grips,"unexpected_grips":unexpected_grips,"no_chord_shape":result.no_chord_shape,"incomplete_arpeggio":result.incomplete_arpeggio});
    write_json(&format!("{label}-summary"), &summary);
    write_json(&format!("{label}-observed"), &result);
    write_json(&format!("{label}-config"), config);
    println!("{label}: keys={} basics={}/{} grips={}/{} missing_grips={} no_shape={} incomplete_arp={} elapsed={:.2}s",result.key_modes.len(),result.basics.len(),expected.basics.len(),result.chord_grips.len(),expected.feasible_grips.len(),missing_grips.len(),result.no_chord_shape,result.incomplete_arpeggio,start.elapsed().as_secs_f64());
    assert!(
        unexpected_grips.is_empty(),
        "planner emitted shape combination rejected by independent feasibility oracle"
    );
    result
}

fn assert_core_coverage(observed: &Observed) {
    assert_eq!(observed.key_modes.len(), 84);
    assert_eq!(
        observed.basics.len(),
        1176,
        "see generated missing_basics list"
    );
    assert_eq!(observed.no_chord_shape, 0);
    assert_eq!(observed.incomplete_arpeggio, 0);
    for task in ["chord", "arpeggio_detached"] {
        let stats = &observed.tasks[task];
        assert_eq!(stats.regions.len(), 5);
        assert_eq!(stats.root_strings.len(), 6);
        assert_eq!(stats.lowest_pitch_members.len(), 4);
    }
}

#[test]
#[ignore = "3.2 million event finite coverage audit; writes coverage evidence under target/coverage/"]
fn large_training_coverage() {
    let mut config =
        Config::load(Some(Path::new("tests/fixtures/legacy-seven-mode.toml"))).unwrap();
    config.simulation.extensions = false;
    config.simulation.ambient = false;
    let expected = expected(&config);
    assert_eq!(expected.basics.len(), 1176);
    write_json("expected", &expected);
    let default = run("basic-million", &config, 1_000_000, &expected, SEED, false);
    config.simulation.extensions = true;
    config.simulation.ambient = true;
    let advanced = run("advanced-200k", &config, 200_000, &expected, SEED, false);
    let advanced_million = run(
        "advanced-two-million",
        &config,
        2_000_000,
        &expected,
        SEED,
        false,
    );
    assert_core_coverage(&advanced_million);
    assert_core_coverage(&default);
    assert_core_coverage(&advanced);
    for role in [
        "diatonic",
        "bridge",
        "arrival",
        "mode_change",
        "secondary",
        "substitute",
        "borrowed",
    ] {
        assert!(advanced.roles.contains_key(role), "missing role {role}");
    }
    assert_eq!(advanced.ambient_colors.len(), 5);
    // Feasible grip missing lists are evidence, NOT a claim of exhaustive arbitrary
    // voicings or a random-run guarantee. No hidden arpeggio shape earns coverage.
}

fn presentation_distribution(observed: &Observed, expected: &Expected) -> Value {
    let mut counts: Vec<_> = expected
        .feasible_grips
        .iter()
        .map(|label| *observed.grip_presentations.get(label).unwrap_or(&0))
        .collect();
    counts.sort_unstable();
    json!({"population":counts.len(),"includes_unseen_as_zero":true,"min":counts[0],"median":counts[(counts.len()-1)/2],"p95":counts[(counts.len()*95).div_ceil(100)-1],"max":counts[counts.len()-1],"seen_once":counts.iter().filter(|n|**n==1).count(),"seen_at_least_ten":counts.iter().filter(|n|**n>=10).count()})
}

#[test]
#[ignore = "per-seed exact finite coverage; at most five million events each"]
fn multi_seed_convergence() {
    let mut config =
        Config::load(Some(Path::new("tests/fixtures/legacy-seven-mode.toml"))).unwrap();
    config.simulation.extensions = true;
    config.simulation.ambient = true;
    let expected = expected(&config);
    let mut failures = Vec::new();
    for seed in [SEED, 42, 7] {
        let label = format!("convergence-seed-{seed}");
        let observed = run(&label, &config, 5_000_000, &expected, seed, true);
        assert_core_coverage(&observed);
        if observed.chord_grips.len() != expected.feasible_grips.len() {
            failures.push(seed);
        }
    }
    assert!(failures.is_empty(), "coverage incomplete at explicit 5m upper bound for seeds {failures:?}; see missing_grips lists, not a plateau-based pass");
}

#[test]
#[ignore = "current daily two-mode cycle: three independent seeds, exact bucket and physical-grip coverage"]
fn daily_cycle_convergence() {
    let config = Config::load(None).unwrap();
    let expected = expected(&config);
    write_json("daily-expected", &expected);
    assert_eq!(expected.basics.len(), 336);
    for seed in [SEED, 42, 7] {
        let observed = run(
            &format!("daily-seed-{seed}"),
            &config,
            2_000_000,
            &expected,
            seed,
            true,
        );
        assert_eq!(observed.key_modes.len(), 24);
        assert_eq!(observed.basics, expected.basics);
        assert_eq!(
            observed.chord_grips, expected.feasible_grips,
            "see missing_grips in report"
        );
        assert_eq!(
            observed.physical_grips, expected.physical_grips,
            "see missing_physical_grips in report"
        );
        assert_eq!(
            (observed.no_chord_shape, observed.incomplete_arpeggio),
            (0, 0)
        );
        assert!(observed.ambient_colors.is_empty());
        for task in ["chord", "arpeggio_detached"] {
            let stats = &observed.tasks[task];
            assert_eq!(stats.basics, expected.basics);
            assert_eq!(stats.regions.len(), 5);
            assert_eq!(stats.root_strings.len(), 6);
        }
        for role in [
            "secondary",
            "substitute",
            "sd25_ii",
            "sd25_v",
            "ssd25_ii",
            "ssd25_v",
        ] {
            assert!(observed.roles.contains_key(role), "missing approach {role}");
        }
        assert!(!observed.roles.contains_key("borrowed"));
        assert!(observed.roles.contains_key("minor_dominant"));
    }
}
