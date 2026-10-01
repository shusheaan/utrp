use std::collections::BTreeMap;
use utrp::{
    config::{Config, Templates},
    progression::Progression,
    session::{Action, Session},
    simulator,
};

fn generator(config: &Config, seed: u64) -> Progression {
    Progression::new(
        config.simulation.clone(),
        Templates::load(None).unwrap(),
        seed,
    )
    .unwrap()
}

#[test]
fn counts_track_consumed_targets_not_planned_phrases_and_reset_per_run() {
    let config = Config::load(None).unwrap();
    let mut engine = generator(&config, 42);
    assert_eq!(engine.key_practice().len(), 24);
    assert!(engine.key_practice().values().all(|n| *n == 0));
    let mut expected = engine.key_practice().clone();
    for n in 1..=4000 {
        let event = engine.next_event();
        *expected.entry(event.key.label()).or_default() += 1;
        assert_eq!(engine.key_practice(), &expected);
        assert_eq!(engine.key_practice().values().sum::<usize>(), n);
    }
    assert!(generator(&config, 42)
        .key_practice()
        .values()
        .all(|n| *n == 0));
}

#[test]
fn preview_history_pause_speed_and_stop_do_not_inflate_key_amounts() {
    let config = Config::load(None).unwrap();
    let stream = simulator::stream(&config, Templates::load(None).unwrap(), 42, 48).unwrap();
    let mut session = Session::new(stream, config.session, 0);
    let original = session.key_practice().clone();
    assert_eq!(original.values().sum::<usize>(), 1);
    for _ in 0..20 {
        assert!(session.phrase_events().len() > 1);
        for action in [Action::Faster, Action::Slower, Action::Pause, Action::Pause] {
            let id = session.target().music.id;
            session.apply(action, 0, id);
        }
    }
    assert_eq!(session.key_practice(), &original);
    for action in [
        Action::Confirm,
        Action::Previous,
        Action::Next,
        Action::Previous,
        Action::Next,
    ] {
        let id = session.target().music.id;
        session.apply(action, 1, id);
    }
    assert_eq!(session.key_practice().values().sum::<usize>(), 2);
    let id = session.target().music.id;
    session.apply(Action::Tick, 10_001, id);
    // Leaving this target via Previous already finalized it as skipped.
    // Timing out its replay must not rewrite that original outcome.
    assert_eq!(session.summary(10_001).timed_out, 0);
    assert_eq!(session.summary(10_001).skipped, 1);
    assert_eq!(session.key_practice().values().sum::<usize>(), 3);
    let id = session.target().music.id;
    let deadline = 10_001 + session.remaining_ms(10_001).unwrap();
    session.apply(Action::Tick, deadline, id);
    assert_eq!(session.summary(deadline).timed_out, 1);
    assert_eq!(session.key_practice().values().sum::<usize>(), 4);
    let before = session.key_practice().clone();
    let id = session.target().music.id;
    session.apply(Action::Stop, deadline + 1, id);
    assert_eq!(session.key_practice(), &before);
}

#[test]
fn default_scope_balances_actual_amounts_even_with_high_return_probability() {
    let mut config = Config::load(None).unwrap();
    let events = std::env::var("UTRP_BALANCE_EVENTS")
        .map(|value| {
            value
                .parse::<usize>()
                .expect("valid balance audit event count")
        })
        .unwrap_or(10_000);
    assert!(events >= 10_000);
    for (probability, return_probability) in [(0.001, 1.0), (0.5, 1.0), (1.0, 1.0), (0.5, 0.2)] {
        config.simulation.modulation_probability = probability;
        config.simulation.modulation_return_probability = return_probability;
        for seed in [7, 42, 20261001] {
            let mut engine = generator(&config, seed);
            for _ in 0..events {
                engine.next_event();
            }
            let counts = engine.key_practice();
            let min = *counts.values().min().unwrap();
            let max = *counts.values().max().unwrap();
            assert_eq!(counts.values().sum::<usize>(), events);
            assert!(min > 0);
            // At a snapshot, a complete 40-item cycle/bridge may overshoot
            // the tolerance. This is NOT a strict per-chord 40-target bound.
            assert!(
                max - min <= 124,
                "seed={seed}, p={probability}, min={min}, max={max}"
            );
            println!("balance: seed={seed} events={events} p={probability} return={return_probability} min={min} max={max} spread={}", max - min);
        }
    }
}

#[test]
fn exploration_chooses_least_practiced_and_back_respects_tolerance() {
    let mut config = Config::load(None).unwrap();
    config.simulation.modulation_return_probability = 1.0;
    config.simulation.modulation_probability = 1.0;
    let mut engine = generator(&config, 42);
    let first = engine.next_event();
    let mut current = first.key;
    let mut previous = None;
    let mut changes = 0;
    let mut blocked_returns = 0;
    for _ in 0..8000 {
        let before = engine.key_practice().clone();
        let event = engine.next_event();
        if event.key == current {
            continue;
        }
        changes += 1;
        let min = before
            .iter()
            .filter(|(k, _)| **k != current.label())
            .map(|(_, n)| *n)
            .min()
            .unwrap();
        let target_amount = before[&event.key.label()];
        if previous.as_ref() == Some(&event.key) {
            assert!(target_amount.saturating_sub(min) <= config.simulation.key_balance_tolerance);
        } else {
            assert_eq!(target_amount, min);
            if let Some(old) = &previous {
                blocked_returns += usize::from(
                    before[&old.label()].saturating_sub(min)
                        > config.simulation.key_balance_tolerance,
                );
            }
        }
        previous = Some(current);
        current = event.key;
    }
    assert!(changes > 100 && blocked_returns > 0);
}

#[test]
fn excess_practice_leaves_at_cycle_boundary_but_zero_probability_still_disables_modulation() {
    let mut config = Config::load(None).unwrap();
    config.simulation.approaches = false; // This test bounds the original 40-item bare cycle.
    config.simulation.modulation_probability = 0.0000001;
    let mut engine = generator(&config, 42);
    let mut previous = engine.next_event();
    let original = previous.key.clone();
    let mut changed = false;
    for _ in 0..100 {
        let event = engine.next_event();
        if event.key != original {
            assert!(event.id <= 79);
            assert_eq!(previous.cycle.unwrap().step, 40);
            changed = true;
            break;
        }
        previous = event;
    }
    assert!(changed);
    config.simulation.modulation_probability = 0.0;
    let mut engine = generator(&config, 42);
    for _ in 0..1000 {
        assert_eq!(engine.next_event().key, original);
    }
}

#[test]
fn log_summary_exposes_counts_without_resuming_them_in_new_session() {
    let mut config = Config::load(None).unwrap();
    let directory = std::env::temp_dir().join(format!("utrp-key-balance-{}", std::process::id()));
    config.storage.directory = Some(directory.clone());
    let mut session = Session::new(
        simulator::stream(&config, Templates::load(None).unwrap(), 42, 48).unwrap(),
        config.session.clone(),
        0,
    );
    let mut log = utrp::storage::Log::open(&config.storage, &config, 42, "guitar")
        .unwrap()
        .unwrap();
    log.update(&session, Action::Tick, 0).unwrap();
    let id = session.target().music.id;
    session.apply(Action::Stop, 1, id);
    log.update(&session, Action::Stop, 1).unwrap();
    let text = std::fs::read_to_string(&log.path).unwrap();
    let summary: serde_json::Value = serde_json::from_str(text.lines().last().unwrap()).unwrap();
    let counts: BTreeMap<String, usize> =
        serde_json::from_value(summary["key_practice"].clone()).unwrap();
    assert_eq!(&counts, session.key_practice());
    assert!(generator(&config, 42)
        .key_practice()
        .values()
        .all(|n| *n == 0));
    drop(log);
    std::fs::remove_dir_all(directory).unwrap();
}
