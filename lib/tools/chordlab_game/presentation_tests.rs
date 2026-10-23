use super::*;
use utrp::theory::key::{Key, Mode};

#[test]
fn approaches_use_destination_relative_palette_and_targets_keep_major_palette() {
    let mut source = Planner::new(0).unwrap().engine.next_event();
    source.key = Key {
        tonic: Tone::parse("C").unwrap(),
        mode: Mode::Ionian,
    };
    for degree in 1..=7 {
        let mut goal = source.clone();
        goal.chord = goal.key.chord(degree, true);
        goal.role = "diatonic".into();
        if !goal.chord.tonicizable() {
            continue;
        }
        let [ii, v] = goal.chord.approach_ii_v(false).unwrap();
        source.chord = ii;
        source.role = "sd25_ii".into();
        assert_eq!(labels::capsule(&source, &goal).1, 1, "local ii is green");
        source.chord = v;
        source.role = "sd25_v".into();
        assert_eq!(labels::capsule(&source, &goal).1, 2, "local V is orange");
        let [ii, v] = goal.chord.approach_ii_v(true).unwrap();
        source.chord = ii;
        source.role = "ssd25_ii".into();
        assert_eq!(
            labels::capsule(&source, &goal).1,
            3,
            "substitute-related bvi is blue"
        );
        source.chord = v;
        source.role = "ssd25_v".into();
        assert_eq!(
            labels::capsule(&source, &goal).1,
            1,
            "subV root is bII, green"
        );
        assert_eq!(
            labels::capsule(&goal, &goal).1,
            [0, 1, 1, 2, 2, 3, 3][degree as usize - 1]
        );
    }
    source.key = Key {
        tonic: Tone::parse("A").unwrap(),
        mode: Mode::Aeolian,
    };
    source.chord = source.key.chord(1, true);
    source.role = "diatonic".into();
    assert_eq!(
        labels::capsule(&source, &source).1,
        3,
        "minor tonic keeps relative-major VI blue"
    );
}

#[test]
fn three_committed_groups_fit_queue_and_preserve_all_resolutions() {
    for seed in 0..12 {
        let mut planner = Planner::new(seed).unwrap();
        assert!(planner.configure(1.0, 2, true));
        let mut queue = VecDeque::new();
        let mut endpoints = 0;
        while endpoints < 3 {
            let target = planner.next_target().unwrap();
            endpoints += target.backbone;
            queue.push_back(target);
        }
        let mut previous_group = 0;
        let mut group_length = 0;
        for _ in 0..300 {
            let current = queue.pop_front().unwrap();
            assert!(current.group >= current.id && current.group >= previous_group);
            group_length = if current.group == previous_group {
                group_length + 1
            } else {
                1
            };
            assert!(
                group_length <= 3,
                "each UI row has exactly three available slots"
            );
            previous_group = current.group;
            if current.backbone != 0 {
                assert_eq!(current.group, current.id);
            }
            assert!(planner.complete(current.id, true));
            let needed = if current.backbone != 0 { 2 } else { 3 };
            let mut endpoints = queue.iter().filter(|t| t.backbone != 0).count();
            while endpoints < needed {
                let next = planner
                    .next_target()
                    .expect("complete three groups fit bounded queue");
                endpoints += usize::from(next.backbone != 0);
                queue.push_back(next);
            }
            for target in &queue {
                if target.backbone == 0 {
                    let goal = queue
                        .iter()
                        .find(|other| other.id == target.group)
                        .expect("no hidden resolution");
                    assert_eq!(target.visit, goal.visit);
                }
            }
            assert!(queue.len() <= 9);
        }
    }
}

#[test]
fn committed_game_session_balances_completed_keys_not_preview_counts() {
    use std::collections::BTreeMap;
    let mut planner = Planner::new(20261023).unwrap();
    assert!(planner.configure(0.5, 2, true));
    let mut queue = VecDeque::new();
    let mut counts = BTreeMap::<(i32, i32), [usize; 3]>::new();
    let mut chords = BTreeMap::<(i32, i32, i32, i32), usize>::new();
    let mut needed = 3;
    let mut visit = 0;
    let mut coverage = 0u8;
    for round in 0..4800 {
        while queue.iter().filter(|t: &&Target| t.backbone != 0).count() < needed {
            queue.push_back(planner.next_target().expect("valid committed preview"));
        }
        let current = queue.pop_front().unwrap();
        if current.visit != visit {
            if visit != 0 {
                assert_eq!(
                    coverage, 127,
                    "no modulation before successful degree coverage"
                );
            }
            visit = current.visit;
            coverage = 0;
        }
        let success = round % 11 != 10;
        // Count only the actual exercise, never queued lookahead or demo frames.
        let count = counts.entry((current.tonic, current.minor)).or_default();
        count[0] += 1;
        count[if success { 1 } else { 2 }] += 1;
        *chords
            .entry((current.tonic, current.minor, current.root, current.quality))
            .or_default() += 1;
        assert!(planner.complete(current.id, success));
        assert!(
            !planner.complete(current.id, success),
            "duplicate completion rejected"
        );
        if success && current.backbone != 0 {
            coverage |= 1 << current.degree;
        }
        needed = if current.backbone != 0 { 2 } else { 3 };
    }
    assert_eq!(counts.len(), 24, "all major/minor keys visited");
    assert_eq!(counts.values().map(|n| n[0]).sum::<usize>(), 4800);
    assert!(counts.values().all(|n| n[0] == n[1] + n[2]));
    let min = counts.values().map(|n| n[1]).min().unwrap();
    let max = counts.values().map(|n| n[1]).max().unwrap();
    assert!(
        min > 0 && max < min * 2,
        "successful exposure should stay comparable: {min}..{max}"
    );
    println!("4800 actual exercises, 24 keys, {} key/chord identities, successful/key={min}..{max}; counts(pitch class, minor)={counts:?}", chords.len());
}
