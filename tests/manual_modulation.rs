use std::collections::BTreeSet;
use utrp::{
    config::{Config, Templates},
    progression::{ChordEvent, ManualModulation, Progression},
    session::{Action, Session},
    simulator,
    theory::key::Mode,
};

fn config() -> Config {
    let mut c = Config::load(None).unwrap();
    c.simulation.modulation_probability = 0.0;
    c.simulation.approaches = false;
    c
}
fn engine(c: &Config, seed: u64) -> Progression {
    Progression::new(c.simulation.clone(), Templates::load(None).unwrap(), seed).unwrap()
}
fn arrival(p: &mut Progression) -> ChordEvent {
    for _ in 0..20 {
        let e = p.next_event();
        if matches!(e.role.as_str(), "arrival" | "mode_change") {
            return e;
        }
    }
    panic!("no arrival within a complete transition");
}
fn session(c: &Config) -> Session {
    Session::new(
        simulator::stream(c, Templates::load(None).unwrap(), 42, 48).unwrap(),
        c.session.clone(),
        0,
    )
}
fn apply(s: &mut Session, a: Action) {
    s.apply(a, 0, s.target().music.id);
}

#[test]
fn manual_waits_one_chord_discards_old_cycle_and_restarts_new_cycle() {
    let c = config();
    let mut p = engine(&c, 42);
    let first = p.next_event();
    p.request_manual(ManualModulation::Balanced, first.id);
    assert!(p.pending_manual_label().unwrap().contains("NEXT"));
    let next = p.next_event();
    assert_eq!(next.key, first.key);
    assert_eq!(next.cycle.unwrap().step, 2);
    assert!(p.pending_manual_label().unwrap().contains("CURRENT"));
    let landed = arrival(&mut p);
    assert_ne!(landed.key, first.key);
    assert_eq!(landed.cycle.unwrap().step, 1);
    assert!(p.pending_manual_label().is_none());
    let mut id = landed.id;
    for step in 2..=40 {
        let e = p.next_event();
        id += 1;
        assert_eq!(e.id, id);
        assert_eq!(e.key, landed.key);
        assert_eq!(e.cycle.unwrap().step, step);
    }
    assert_eq!(p.key_practice().values().sum::<usize>(), id + 1);
    let e = p.next_event();
    assert_eq!(e.key, landed.key);
    assert_eq!(e.cycle.unwrap().step, 2);
}

#[test]
fn next_chord_and_remaining_preview_are_not_replaced_until_boundary() {
    let c = config();
    let mut s = session(&c);
    let preview = s.phrase_events()[1].clone();
    apply(&mut s, Action::ModulateBalanced);
    apply(&mut s, Action::Confirm);
    assert_eq!(s.target().music, preview);
    apply(&mut s, Action::Confirm);
    assert_ne!(s.target().music.key, s.history[0].music.key);
    assert_eq!(s.summary(0).confirmed, 2);
    assert_eq!(s.summary(0).presented, 3);
    let saved = s.target().clone();
    let amounts = s.key_practice().clone();
    apply(&mut s, Action::Previous);
    apply(&mut s, Action::ModulateBalanced);
    assert!(s.manual_notice().contains("latest target"));
    assert!(s.pending_manual_label().is_none());
    apply(&mut s, Action::Next);
    assert_eq!(s.target(), &saved);
    assert_eq!(s.key_practice(), &amounts);
}

#[test]
fn unavailable_back_does_not_cancel_pending_and_repetition_does_not_delay_it() {
    let mut p = engine(&config(), 42);
    let a = p.next_event();
    p.request_manual(ManualModulation::Back, a.id);
    assert!(p.manual_notice().contains("no previous key"));
    assert!(p.pending_manual_label().is_none());
    p.request_manual(ManualModulation::Balanced, a.id);
    p.request_manual(ManualModulation::Back, a.id);
    assert!(p.pending_manual_label().unwrap().contains("E balanced"));
    let b = p.next_event();
    for _ in 0..20 {
        p.request_manual(ManualModulation::Balanced, b.id);
    }
    assert!(p.pending_manual_label().unwrap().contains("CURRENT"));
    assert_ne!(p.next_event().key, a.key);
}

#[test]
fn back_overrides_balance_and_replacement_preserves_ready_boundary() {
    let mut p = engine(&config(), 42);
    let a = p.next_event();
    p.request_manual(ManualModulation::Balanced, a.id);
    let b = arrival(&mut p);
    p.request_manual(ManualModulation::Balanced, b.id);
    let next = p.next_event();
    assert_eq!(next.key, b.key);
    p.request_manual(ManualModulation::Back, next.id);
    assert!(p
        .pending_manual_label()
        .unwrap()
        .contains("Q back: after CURRENT"));
    let returned = arrival(&mut p);
    assert_eq!(returned.key, a.key); // despite other unpracticed keys
    assert_eq!(returned.cycle.unwrap().step, 1); // not old step 3
    p.request_manual(ManualModulation::Back, returned.id);
    assert_eq!(arrival(&mut p).key, b.key); // previous key, not original key
}

#[test]
fn pending_during_bridge_waits_for_arrival_even_when_replaced() {
    let mut p = engine(&config(), 42);
    let a = p.next_event();
    p.request_manual(ManualModulation::Balanced, a.id);
    p.next_event();
    let bridge = p.next_event();
    assert!(matches!(
        bridge.role.as_str(),
        "bridge" | "shared_pivot" | "diminished_pivot"
    ));
    p.request_manual(ManualModulation::Back, bridge.id);
    let landed = arrival(&mut p);
    assert_eq!(landed.key, bridge.key);
    assert!(p.pending_manual_label().unwrap().contains("CURRENT"));
    assert_eq!(arrival(&mut p).key, a.key);
}

#[test]
fn all_four_approaches_and_primary_dominants_finish_before_manual_modulation() {
    for kind in 0..4 {
        for chunk in [1, 5, 8] {
            let mut c = config();
            c.simulation.approaches = true;
            c.simulation.cycle_chunk_size = chunk;
            c.simulation.secondary_probability = f64::from(kind == 0);
            c.simulation.substitution_probability = f64::from(kind == 1);
            c.simulation.sd25_probability = f64::from(kind == 2);
            c.simulation.ssd25_probability = f64::from(kind == 3);
            c.simulation.borrow_probability = 0.0;
            let mut p = engine(&c, 42);
            let a = p.next_event();
            p.request_manual(ManualModulation::Balanced, a.id);
            for _ in 0..if kind < 2 { 1 } else { 2 } {
                let approach = p.next_event();
                assert_eq!(approach.key, a.key);
                assert!(approach.cycle.is_none());
                assert!(!p.pending_manual_label().unwrap().contains("CURRENT"));
            }
            let target = p.next_event();
            assert_eq!(target.key, a.key);
            assert_eq!(target.cycle.unwrap().step, 2);
            assert_ne!(p.next_event().key, a.key);
        }
    }
    for mode in [Mode::Ionian, Mode::Aeolian] {
        let mut c = config();
        c.simulation.modes = vec![mode];
        c.simulation.cycle_chunk_size = 1;
        c.simulation.seventh_probability = 1.0;
        c.simulation.minor_dominant_probability = 1.0;
        let mut p = engine(&c, 42);
        let before = (0..24).map(|_| p.next_event()).last().unwrap();
        assert_eq!(before.cycle.as_ref().unwrap().step, 24);
        p.request_manual(ManualModulation::Balanced, before.id);
        let v = p.next_event();
        assert_eq!(v.degree, Some(5));
        assert_eq!(v.chord.quality, "7");
        let tonic = p.next_event();
        assert_eq!(tonic.key, before.key);
        assert_eq!(tonic.degree, Some(1));
        assert_ne!(p.next_event().key, before.key);
    }
}

#[test]
fn pending_request_suppresses_automatic_change_at_old_cycle_end() {
    let mut c = config();
    c.simulation.modulation_probability = 1.0;
    let mut p = engine(&c, 42);
    let end = (0..40).map(|_| p.next_event()).last().unwrap();
    assert_eq!(end.cycle.unwrap().step, 40);
    p.request_manual(ManualModulation::Balanced, end.id);
    let next = p.next_event();
    assert_eq!(next.key, end.key);
    assert_eq!(next.cycle.unwrap().step, 2);
    assert_ne!(p.next_event().key, end.key);
}

#[test]
fn same_tonic_major_minor_are_reachable_and_single_key_fails_explicitly() {
    let mut c = config();
    c.simulation.keys = vec!["C".into()];
    let mut p = engine(&c, 42);
    let a = p.next_event();
    p.request_manual(ManualModulation::Balanced, a.id);
    let b = arrival(&mut p);
    assert_eq!(a.key.tonic, b.key.tonic);
    assert_ne!(a.key.mode, b.key.mode);
    assert_eq!(b.role, "mode_change");
    c.simulation.modes = vec![Mode::Ionian];
    let mut p = engine(&c, 42);
    let a = p.next_event();
    p.request_manual(ManualModulation::Balanced, a.id);
    assert!(p.manual_notice().contains("no allowed route"));
    assert!(p.pending_manual_label().is_none());
    assert_eq!(p.next_event().key, a.key);
}

#[test]
fn pause_stale_batch_deadline_and_stop_preserve_scoring_semantics() {
    let c = config();
    let mut s = session(&c);
    apply(&mut s, Action::ModulateBack);
    assert!(!s.stopped);
    apply(&mut s, Action::Pause);
    apply(&mut s, Action::ModulateBalanced);
    s.apply(Action::Tick, 100_000, 0);
    assert_eq!(s.history.len(), 1);
    apply(&mut s, Action::Pause);
    apply(&mut s, Action::Confirm);
    assert!(!s.apply(Action::ModulateBack, 0, 0));
    assert!(s.pending_manual_label().unwrap().contains("E balanced"));
    let count = s.key_practice().clone();
    apply(&mut s, Action::Stop);
    assert_eq!(s.summary(0).confirmed, 1);
    assert_eq!(s.key_practice(), &count);
    assert!(!s.apply(Action::Next, 0, 1));
    let mut s = session(&c);
    s.apply(Action::ModulateBalanced, 10_000, 0);
    assert_eq!(s.summary(10_000).timed_out, 1);
    assert!(s.pending_manual_label().is_none()); // deadline wins, no stale request
}

#[test]
fn balanced_manual_stress_chooses_least_practiced_and_all_routes() {
    let mut c = Config::load(None).unwrap();
    c.simulation.modulation_probability = 0.0;
    c.simulation.modulation_return_probability = 1.0; // must NOT bias E
    let mut p = engine(&c, 42);
    let mut previous = p.next_event();
    let mut changed_after = BTreeSet::new();
    let mut routes = BTreeSet::new();
    let mut parallel = false;
    for id in 1..20_000 {
        if id % 7 == 0 {
            p.request_manual(ManualModulation::Balanced, previous.id);
        }
        let amounts = p.key_practice().clone();
        let e = p.next_event();
        assert_eq!(e.id, id);
        if e.key != previous.key {
            let min = amounts
                .iter()
                .filter(|(k, _)| **k != previous.key.label())
                .map(|(_, n)| *n)
                .min()
                .unwrap();
            assert_eq!(amounts[&e.key.label()], min);
            changed_after.insert(previous.role.clone());
            routes.insert(e.role.clone());
            parallel |= e.key.tonic.pc == previous.key.tonic.pc;
            assert!(matches!(
                previous.role.as_str(),
                "diatonic" | "arrival" | "mode_change"
            ));
        }
        previous = e;
    }
    assert!(p.key_practice().values().all(|n| *n > 0));
    assert_eq!(p.key_practice().values().sum::<usize>(), 20_000);
    assert_eq!(
        routes,
        ["bridge", "shared_pivot", "diminished_pivot"]
            .map(String::from)
            .into()
    );
    assert!(parallel);
    assert!(changed_after.contains("diatonic"));
    assert!(
        p.key_practice().values().max().unwrap() - p.key_practice().values().min().unwrap() < 30
    );
}

#[test]
fn manual_sessions_keep_real_guitar_targets_and_contiguous_log_ids() {
    let events = std::env::var("UTRP_MANUAL_EVENTS")
        .map(|v| v.parse::<usize>().expect("valid manual audit event count"))
        .unwrap_or(2000);
    assert!(events >= 2000);
    for seed in [7, 42, 20261001] {
        let mut c = Config::load(None).unwrap();
        c.simulation.modulation_probability = 0.0;
        let mut s = Session::new(
            simulator::stream(&c, Templates::load(None).unwrap(), seed, 48).unwrap(),
            c.session.clone(),
            0,
        );
        let mut contexts = BTreeSet::new();
        for id in 0..events {
            let target = s.target();
            assert_eq!(target.music.id, id);
            let positions = if target.guitar.task == "chord" {
                &target
                    .guitar
                    .shape
                    .as_ref()
                    .expect("playable complete grip")
                    .positions
            } else {
                &target.guitar.arpeggio
            };
            assert_eq!(
                positions
                    .iter()
                    .map(|p| p.midi % 12)
                    .collect::<BTreeSet<_>>(),
                target.music.chord.pcs().into_iter().collect()
            );
            for p in positions {
                assert_eq!(p.midi, c.guitar.tuning[usize::from(6 - p.string)] + p.fret);
            }
            contexts.insert((target.guitar.task.clone(), target.guitar.region));
            if id % 17 == 0 {
                apply(&mut s, Action::ModulateBalanced);
            }
            if id + 1 < events {
                apply(&mut s, Action::Confirm);
            }
        }
        apply(&mut s, Action::Stop);
        assert_eq!(s.summary(0).confirmed, events - 1);
        assert_eq!(s.summary(0).stopped, 1);
        assert_eq!(s.key_practice().values().sum::<usize>(), events);
        assert!(s.key_practice().values().all(|n| *n > 0));
        assert_eq!(contexts.len(), 2 * c.guitar.regions.len());
        let min = s.key_practice().values().min().unwrap();
        let max = s.key_practice().values().max().unwrap();
        println!("manual guitar seed={seed} events={events} keys=24 task_regions={} min={min} max={max} spread={}", contexts.len(), max - min);
    }
}

#[test]
fn manual_actions_and_discarded_preview_do_not_corrupt_log_target_ids() {
    let mut c = config();
    let directory = std::env::temp_dir().join(format!("utrp-manual-log-{}", std::process::id()));
    c.storage.directory = Some(directory.clone());
    let mut s = session(&c);
    let mut log = utrp::storage::Log::open(&c.storage, &c, 42, "guitar")
        .unwrap()
        .unwrap();
    for a in [
        Action::Tick,
        Action::ModulateBalanced,
        Action::Confirm,
        Action::Confirm,
        Action::ModulateBack,
        Action::Next,
        Action::Next,
        Action::Next,
        Action::Next,
        Action::Stop,
    ] {
        apply(&mut s, a);
        log.update(&s, a, 0).unwrap();
    }
    let rows: Vec<serde_json::Value> = std::fs::read_to_string(&log.path)
        .unwrap()
        .lines()
        .map(|l| serde_json::from_str(l).unwrap())
        .collect();
    let targets: Vec<_> = rows.iter().filter(|r| r["type"] == "target").collect();
    assert_eq!(targets.len(), s.history.len());
    for (id, target) in targets.iter().enumerate() {
        assert_eq!(target["target"]["music"]["id"], id);
    }
    let attempts: BTreeSet<_> = rows
        .iter()
        .filter(|r| r["type"] == "attempt")
        .map(|r| r["event_id"].as_u64().unwrap())
        .collect();
    assert_eq!(attempts.len(), targets.len());
    for action in ["modulate_balanced", "modulate_back"] {
        assert!(rows
            .iter()
            .any(|r| r["type"] == "action" && r["action"] == action));
    }
    assert_eq!(rows.last().unwrap()["summary"]["presented"], targets.len());
    drop(log);
    std::fs::remove_dir_all(directory).unwrap();
}
