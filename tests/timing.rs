use utrp::{
    config::{Config, Templates},
    session::{Action, Session},
    simulator,
};

fn session() -> Session {
    let c = Config::load(None).unwrap();
    Session::new(
        simulator::stream(&c, Templates::load(None).unwrap(), 42, 48).unwrap(),
        c.session,
        0,
    )
}
fn apply(s: &mut Session, action: Action, now: u64) {
    s.apply(action, now, s.target().music.id);
}

#[test]
fn default_is_untimed_space_scores_and_navigation_does_not() {
    let mut s = session();
    assert!(!s.automatic);
    assert_eq!(s.seconds, 10.0);
    assert_eq!(s.turn_limit, None);
    apply(&mut s, Action::Tick, 86_400_000);
    assert_eq!(s.index, 0);
    assert_eq!(s.remaining_ms(86_400_000), None);
    apply(&mut s, Action::Confirm, 86_400_001);
    assert_eq!(s.summary(86_400_001).confirmed, 1);
    let saved = s.target().clone();
    apply(&mut s, Action::Previous, 86_400_002);
    apply(&mut s, Action::Next, 86_400_003);
    assert_eq!(s.target(), &saved);
    apply(&mut s, Action::Next, 86_400_004);
    assert_eq!(s.summary(86_400_004).confirmed, 1);
    assert_eq!(s.summary(86_400_004).skipped, 1);
    assert_eq!(s.summary(86_400_004).timed_out, 0);
}

#[test]
fn enabling_starts_ten_seconds_from_now_then_times_out_without_credit() {
    let mut s = session();
    apply(&mut s, Action::ToggleAuto, 120_000);
    assert!(s.automatic);
    assert_eq!(s.index, 0);
    assert_eq!(s.turn_limit, Some(10_000));
    assert_eq!(s.remaining_ms(120_000), Some(10_000));
    apply(&mut s, Action::Tick, 129_999);
    assert_eq!(s.index, 0);
    apply(&mut s, Action::Tick, 130_000);
    assert_eq!(s.index, 1);
    assert_eq!(s.summary(130_000).timed_out, 1);
    assert_eq!(s.summary(130_000).confirmed, 0);
    assert_eq!(s.remaining_ms(130_000), Some(10_000));
}

#[test]
fn disabling_cancels_deadline_without_advancing_or_scoring() {
    let mut s = session();
    apply(&mut s, Action::ToggleAuto, 1000);
    apply(&mut s, Action::ToggleAuto, 10_999);
    assert!(!s.automatic);
    assert_eq!(s.index, 0);
    assert_eq!(s.turn_limit, None);
    assert!(s.attempts[0].is_none());
    apply(&mut s, Action::Tick, 100_000);
    assert_eq!(s.index, 0);
    apply(&mut s, Action::Confirm, 100_001);
    assert_eq!(s.summary(100_001).confirmed, 1);
    assert_eq!(s.summary(100_001).timed_out, 0);
    assert_eq!(s.attempts[0].as_ref().unwrap().limit_ms, None);
}

#[test]
fn speed_changes_affect_next_target_and_survive_toggle() {
    let mut s = session();
    apply(&mut s, Action::ToggleAuto, 0);
    apply(&mut s, Action::Faster, 1000);
    assert_eq!(s.seconds, 9.0);
    assert_eq!(s.remaining_ms(1000), Some(9000)); // current still expires at 10s
    apply(&mut s, Action::Confirm, 2000);
    assert_eq!(s.remaining_ms(2000), Some(9000));
    apply(&mut s, Action::ToggleAuto, 3000);
    apply(&mut s, Action::ToggleAuto, 90_000);
    assert_eq!(s.remaining_ms(90_000), Some(9000));
    apply(&mut s, Action::Slower, 90_001);
    apply(&mut s, Action::Confirm, 90_002);
    assert_eq!(s.remaining_ms(90_002), Some(10_000));
}

#[test]
fn enabling_while_paused_waits_for_resume_and_disabling_removes_timer() {
    let mut s = session();
    apply(&mut s, Action::Pause, 1000);
    apply(&mut s, Action::ToggleAuto, 2000);
    apply(&mut s, Action::Tick, 100_000);
    assert_eq!(s.index, 0);
    assert_eq!(s.remaining_ms(100_000), Some(10_000));
    apply(&mut s, Action::Pause, 100_001);
    assert_eq!(s.remaining_ms(100_001), Some(10_000));
    apply(&mut s, Action::Pause, 102_001);
    apply(&mut s, Action::ToggleAuto, 102_002);
    apply(&mut s, Action::Pause, 110_001);
    assert_eq!(s.remaining_ms(110_001), None);
    apply(&mut s, Action::Tick, 200_000);
    assert_eq!(s.index, 0);
    assert_eq!(s.summary(200_000).timed_out, 0);
}

#[test]
fn toggle_at_deadline_cannot_apply_to_successor_or_erase_timeout() {
    let mut s = session();
    apply(&mut s, Action::ToggleAuto, 0);
    s.apply(Action::ToggleAuto, 10_000, 0);
    assert_eq!(s.index, 1);
    assert!(s.automatic);
    assert_eq!(s.summary(10_000).timed_out, 1);
    assert!(!s.apply(Action::ToggleAuto, 10_000, 0));
    apply(&mut s, Action::ToggleAuto, 10_001);
    assert!(!s.automatic);
    assert_eq!(s.index, 1);
}
