use utrp::{
    config::{Config, Templates},
    guitar::{self, GuitarPlanner},
    progression::Progression,
    session::{Action, Outcome, Session},
    simulator,
    theory::{
        chord::Chord,
        key::{Key, Mode},
        tone::Tone,
    },
};

fn config() -> Config {
    Config::load(Some(std::path::Path::new(
        "tests/fixtures/legacy-seven-mode.toml",
    )))
    .unwrap()
}
fn templates() -> Templates {
    Templates::load(None).unwrap()
}
fn session() -> Session {
    let c = config();
    Session::new(
        simulator::stream(&c, templates(), 42, 48).unwrap(),
        c.session,
        0,
    )
}
fn apply(s: &mut Session, a: Action, now: u64) {
    let id = s.target().music.id;
    s.apply(a, now, id);
}

#[test]
fn score_only_space_and_no_history_farming() {
    let mut s = session();
    let first = s.target().clone();
    apply(&mut s, Action::Confirm, 1000);
    assert_eq!(s.summary(1000).confirmed, 1);
    apply(&mut s, Action::Previous, 2000);
    assert_eq!(s.target(), &first);
    apply(&mut s, Action::Confirm, 2500);
    assert_eq!(s.summary(2500).confirmed, 1);
    assert_eq!(s.summary(2500).skipped, 1);
    apply(&mut s, Action::Next, 3000);
    assert_eq!(s.summary(3000).confirmed, 1);
}
#[test]
fn deadline_space_is_timeout_not_confirmation_of_successor() {
    let mut s = session();
    let id = s.target().music.id;
    s.apply(Action::Confirm, 10000, id);
    assert_eq!(s.index, 1);
    assert_eq!(s.summary(10000).confirmed, 0);
    assert_eq!(s.summary(10000).timed_out, 1);
    s.apply(Action::Confirm, 10000, id);
    assert_eq!(s.index, 1);
    apply(&mut s, Action::Previous, 11000);
    apply(&mut s, Action::Confirm, 12000);
    assert_eq!(s.summary(12000).confirmed, 0);
}
#[test]
fn speed_change_applies_to_next_chord_only() {
    let mut s = session();
    apply(&mut s, Action::Faster, 1000);
    assert_eq!(s.seconds, 9.0);
    assert_eq!(s.remaining_ms(1000), Some(9000));
    apply(&mut s, Action::Tick, 10000);
    assert_eq!(s.index, 1);
    assert_eq!(s.remaining_ms(10000), Some(9000));
    apply(&mut s, Action::Slower, 11000);
    assert_eq!(s.remaining_ms(11000), Some(8000));
    apply(&mut s, Action::Confirm, 12000);
    assert_eq!(s.remaining_ms(12000), Some(10000));
}
#[test]
fn pause_does_not_timeout_and_keeps_remaining_time() {
    let mut s = session();
    apply(&mut s, Action::Pause, 2000);
    apply(&mut s, Action::Tick, 100000);
    assert_eq!(s.index, 0);
    assert_eq!(s.remaining_ms(100000), Some(8000));
    apply(&mut s, Action::Pause, 102000);
    assert_eq!(s.elapsed_ms(102000), 2000);
    apply(&mut s, Action::Tick, 110000);
    assert_eq!(s.index, 1);
}
#[test]
fn manual_no_deadline_and_stop_has_no_total_limit() {
    let mut s = session();
    apply(&mut s, Action::ToggleAuto, 1000);
    apply(&mut s, Action::Tick, 86400000);
    assert_eq!(s.index, 0);
    assert_eq!(s.remaining_ms(86400000), None);
    apply(&mut s, Action::Stop, 86400001);
    assert!(s.stopped);
    assert_eq!(s.summary(86400001).score, 0);
    apply(&mut s, Action::Confirm, 86400002);
    assert_eq!(s.index, 0);
}
#[test]
fn navigation_resets_deadline_without_reroll() {
    let mut s = session();
    let first = s.target().clone();
    apply(&mut s, Action::Next, 9000);
    let second = s.target().clone();
    apply(&mut s, Action::Previous, 9500);
    assert_eq!(s.target(), &first);
    apply(&mut s, Action::Next, 10000);
    assert_eq!(s.target(), &second);
    assert_eq!(s.remaining_ms(10000), Some(10000));
}
#[test]
fn stable_music_independent_of_speed_and_history() {
    let mut a = session();
    let mut b = session();
    for i in 0..80 {
        assert_eq!(a.target(), b.target());
        apply(&mut a, Action::Faster, i * 100);
        apply(&mut a, Action::Next, i * 100 + 1);
        apply(&mut b, Action::Next, i * 100 + 1);
    }
}
#[test]
fn all_keys_modes_degrees_have_correct_chord_members() {
    let modes = [
        Mode::Ionian,
        Mode::Dorian,
        Mode::Phrygian,
        Mode::Lydian,
        Mode::Mixolydian,
        Mode::Aeolian,
        Mode::Locrian,
        Mode::HarmonicMinor,
        Mode::MelodicMinor,
    ];
    for name in config().simulation.keys {
        for mode in modes {
            let key = Key {
                tonic: Tone::parse(&name).unwrap(),
                mode,
            };
            let scale = key.scale();
            for degree in 1..=7 {
                for seventh in [false, true] {
                    let c = key.chord(degree, seventh);
                    assert!(!c.quality.contains("color"), "{} {}", key.label(), degree);
                    for (i, tone) in c.tones.iter().enumerate() {
                        assert_eq!(tone, &scale[(usize::from(degree) - 1 + i * 2) % 7]);
                    }
                    for inv in 0..c.tones.len() {
                        let notes = c.piano_notes(inv, 48);
                        assert!(notes.windows(2).all(|n| n[0] < n[1]));
                        assert_eq!(notes[0] % 12, c.tones[inv].pc);
                    }
                }
            }
        }
    }
}
#[test]
fn substitutes_and_diminished_spelling() {
    let key = Key {
        tonic: Tone::parse("C").unwrap(),
        mode: Mode::Ionian,
    };
    let c = key.chord(1, true);
    assert_eq!(c.secondary().symbol(), "G7");
    assert_eq!(c.substitute().symbol(), "Db7");
    let root = Tone::parse("C").unwrap();
    let dim = Chord::from_tones(
        vec![
            root.clone(),
            root.transpose(3, 2),
            root.transpose(6, 4),
            root.transpose(9, 6),
        ],
        vec![1, 3, 5, 7],
    );
    assert_eq!(dim.quality, "dim7");
    assert_eq!(dim.tones[3].name, "Bbb");
    assert!(Tone::parse("Cjunk").is_err());
    assert!(Tone::parse("H").is_err());
}
#[test]
fn diatonic_core_no_accidental_detours() {
    let mut c = config();
    c.simulation.extensions = false;
    c.simulation.ambient = false;
    c.simulation.modulation_probability = 0.0;
    let mut stream = simulator::stream(&c, templates(), 21, 48).unwrap();
    let key = stream.next_target().music.key;
    for _ in 0..300 {
        let event = stream.next_target().music;
        assert_eq!(event.key, key);
        assert_eq!(event.role, "diatonic");
        let scale: Vec<_> = key.scale().iter().map(|t| t.pc).collect();
        assert!(event.chord.pcs().iter().all(|p| scale.contains(p)));
    }
}
#[test]
fn modulation_has_preparation_arrival_and_stable_new_phrase() {
    let mut c = config();
    c.simulation.modes = vec![Mode::Ionian];
    c.simulation.modulation_probability = 1.0;
    c.simulation.minimum_phrases_in_key = 1;
    let mut p = Progression::new(c.simulation, templates(), 7).unwrap();
    let mut events = Vec::new();
    for _ in 0..120 {
        events.push(p.next_event());
    }
    let mut bridges = 0;
    for pair in events.windows(2) {
        if pair[0].role == "bridge" {
            bridges += 1;
            assert_eq!(pair[1].role, "arrival");
            assert_eq!(pair[0].key, pair[1].key);
            assert_eq!((pair[0].chord.root.pc + 5) % 12, pair[1].chord.root.pc);
            assert_ne!(
                pair[0].previous_key.as_ref().unwrap().tonic.pc,
                pair[0].key.tonic.pc
            );
        }
    }
    assert!(bridges > 5);
}
#[test]
fn all_modes_modulate_without_false_modal_dominants() {
    let mut c = config();
    c.simulation.modulation_probability = 1.0;
    c.simulation.minimum_phrases_in_key = 1;
    let mut p = Progression::new(c.simulation, templates(), 12).unwrap();
    let mut modes = std::collections::BTreeSet::new();
    for _ in 0..2000 {
        let e = p.next_event();
        modes.insert(e.key.mode);
        if e.role == "bridge" {
            assert!(matches!(e.key.mode, Mode::Ionian | Mode::Aeolian));
        }
    }
    assert_eq!(modes.len(), 7);
}
#[test]
fn guitar_pitches_members_fingers_and_all_inversions() {
    let c = config();
    let mut inversion_seen = std::collections::BTreeSet::new();
    for name in &c.simulation.keys {
        for mode in &c.simulation.modes {
            for degree in 1..=7 {
                for seventh in [false, true] {
                    let chord = Key {
                        tonic: Tone::parse(name).unwrap(),
                        mode: *mode,
                    }
                    .chord(degree, seventh);
                    let mut count = 0;
                    for region in &c.guitar.regions {
                        for shape in guitar::shapes(&chord, &c.guitar, *region) {
                            count += 1;
                            inversion_seen.insert((seventh, shape.inversion));
                            assert_eq!(shape.positions.len(), chord.tones.len());
                            for p in &shape.positions {
                                assert_eq!(
                                    p.midi,
                                    c.guitar.tuning[(6 - p.string) as usize] + p.fret
                                );
                                assert!(chord.pcs().contains(&(p.midi % 12)));
                                assert!(p.finger.is_some_and(|f| f <= 4));
                            }
                            if let Some(b) = &shape.barre {
                                assert!(!shape.positions.iter().any(|p| p.string <= b.from_string
                                    && p.string >= b.to_string
                                    && p.fret < b.fret));
                            }
                            assert_eq!(
                                shape.positions[0].midi % 12,
                                chord.tones[shape.inversion].pc
                            );
                        }
                    }
                    assert!(count > 0, "no shape {}", chord.symbol());
                }
            }
        }
    }
    assert_eq!(inversion_seen.len(), 7);
}
#[test]
fn guitar_regions_rotate_and_arpeggio_is_separate() {
    let c = config();
    let mut p = Progression::new(c.simulation.clone(), templates(), 9).unwrap();
    let mut g = GuitarPlanner::new(c.guitar.clone());
    let mut tasks = std::collections::BTreeSet::new();
    for _ in 0..80 {
        let e = p.next_event();
        let t = g.target(&e);
        assert!(c.guitar.regions.contains(&t.region));
        tasks.insert(t.task.clone());
        for pos in t.arpeggio {
            assert!(e.chord.pcs().contains(&(pos.midi % 12)));
        }
    }
    assert!(tasks.contains("arpeggio_detached"));
    assert!(tasks.contains("chord"));
}
#[test]
fn invalid_config_is_explicit() {
    let mut c = config();
    c.session.seconds_per_chord = f64::NAN;
    assert!(c.validate().is_err());
    let mut c = config();
    c.simulation.modulation_probability = 1.01;
    assert!(c.validate().is_err());
    let mut c = config();
    c.guitar.triad_strings = vec![vec![1, 1, 2]];
    assert!(c.validate().is_err());
    let mut c = config();
    c.guitar.tuning[5] = 127;
    assert!(c.validate().is_err());
    assert!(simulator::Options::parse(&["--nonsense".into(), "1".into()]).is_err());
}
#[test]
fn extensions_and_ambient_are_explicit_not_unlabelled_accidentals() {
    let mut c = config();
    c.simulation.extensions = true;
    c.simulation.ambient = true;
    let mut p = Progression::new(c.simulation, templates(), 13).unwrap();
    let mut roles = std::collections::BTreeSet::new();
    let mut colors = 0;
    for _ in 0..1800 {
        let e = p.next_event();
        roles.insert(e.role.clone());
        if e.role == "diatonic" {
            let pcs: Vec<_> = e.key.scale().iter().map(|t| t.pc).collect();
            assert!(e.chord.pcs().iter().all(|p| pcs.contains(p)));
        }
        if e.chord.quality.contains("sus") || e.chord.quality.contains("add9") {
            colors += 1;
        }
    }
    assert!(roles.contains("secondary"));
    assert!(roles.contains("substitute"));
    assert!(colors > 0);
}
#[test]
fn stop_does_not_award_current_target() {
    let mut s = session();
    apply(&mut s, Action::Confirm, 500);
    apply(&mut s, Action::Next, 1000);
    apply(&mut s, Action::Stop, 1500);
    let summary = s.summary(1500);
    assert_eq!(summary.score, 50);
    assert_eq!(summary.stopped, 1);
    assert_eq!(s.attempts[0].as_ref().unwrap().outcome, Outcome::Confirmed);
}

#[test]
fn paused_navigation_does_not_count_pause_as_practice_time() {
    let mut s = session();
    apply(&mut s, Action::Pause, 1000);
    apply(&mut s, Action::Next, 5000);
    apply(&mut s, Action::Pause, 10000);
    assert_eq!(s.elapsed_ms(10000), 1000);
    assert_eq!(s.remaining_ms(10000), Some(10000));
}
#[test]
fn enter_after_deadline_counts_timeout_without_generating_successor() {
    let mut s = session();
    apply(&mut s, Action::Stop, 10000);
    assert!(s.stopped);
    assert_eq!(s.index, 0);
    assert_eq!(s.summary(10000).timed_out, 1);
}
#[test]
fn storage_is_append_only_and_records_unique_attempts() {
    let mut c = config();
    let temp = std::env::temp_dir().join(format!("utrp-log-test-{}", std::process::id()));
    c.storage.directory = Some(temp.clone());
    let mut s = session();
    let mut log = utrp::storage::Log::open(&c.storage, &c, 42, "guitar")
        .unwrap()
        .unwrap();
    log.update(&s, Action::Tick, 0).unwrap();
    apply(&mut s, Action::Confirm, 100);
    log.update(&s, Action::Confirm, 100).unwrap();
    apply(&mut s, Action::Stop, 200);
    log.update(&s, Action::Stop, 200).unwrap();
    let contents = std::fs::read_to_string(&log.path).unwrap();
    let rows: Vec<serde_json::Value> = contents
        .lines()
        .map(|l| serde_json::from_str(l).unwrap())
        .collect();
    assert_eq!(rows.iter().filter(|r| r["type"] == "attempt").count(), 2);
    assert_eq!(rows.last().unwrap()["summary"]["confirmed"], 1);
    drop(log);
    std::fs::remove_dir_all(temp).unwrap();
}

#[test]
fn enter_is_not_lost_after_space_in_same_poll_batch() {
    let mut s = session();
    let id = s.target().music.id;
    s.apply(Action::Confirm, 100, id);
    s.apply(Action::Stop, 100, id);
    assert!(s.stopped);
    assert_eq!(s.summary(100).confirmed, 1);
}
#[test]
fn chord_degrees_show_accidentals_not_just_member_numbers() {
    let key = Key {
        tonic: Tone::parse("C").unwrap(),
        mode: Mode::Dorian,
    };
    let c = key.chord(1, true);
    assert_eq!(
        (0..4).map(|i| c.degree_label(i)).collect::<Vec<_>>(),
        vec!["1", "b3", "5", "b7"]
    );
    assert!(Tone::parse("C#b").is_err());
}

#[test]
fn impossible_guitar_region_is_reported_not_faked() {
    let mut c = config();
    c.guitar.regions = vec![[0, 0]];
    c.simulation.keys = vec!["Db".into()];
    c.simulation.modes = vec![Mode::Ionian];
    let mut s = simulator::stream(&c, templates(), 4, 48).unwrap();
    let t = s.next_target();
    assert!(t.guitar.shape.is_none());
    assert!(t.guitar.note.contains("No complete"));
    assert!(simulator::export(&t, "guitar")["chords"][0]["notes"]
        .as_array()
        .unwrap()
        .is_empty());
}
#[test]
fn score_speed_bounds_and_stale_batches() {
    let mut s = session();
    for _ in 0..100 {
        apply(&mut s, Action::Faster, 0);
    }
    assert_eq!(s.seconds, 1.0);
    for _ in 0..100 {
        apply(&mut s, Action::Slower, 0);
    }
    assert_eq!(s.seconds, 60.0);
    let id = s.target().music.id;
    s.apply(Action::Next, 0, id);
    s.apply(Action::Next, 0, id);
    assert_eq!(s.index, 1);
    apply(&mut s, Action::MidiMatch, 1);
    assert_eq!(s.summary(1).midi_matched, 1);
}

#[test]
fn same_tonic_mode_change_is_labelled_separately() {
    let mut c = config();
    c.simulation.keys = vec!["C".into()];
    c.simulation.modulation_probability = 1.0;
    c.simulation.minimum_phrases_in_key = 1;
    let mut p = Progression::new(c.simulation, templates(), 91).unwrap();
    let mut changed = false;
    for _ in 0..100 {
        let e = p.next_event();
        assert_ne!(e.role, "arrival");
        if e.role == "mode_change" {
            changed = true;
            assert!(e.reason.contains("same-tonic"));
        }
    }
    assert!(changed);
}
#[test]
fn public_stream_rejects_invalid_configuration_before_generation() {
    let mut c = Config::load(None).unwrap();
    c.guitar.regions.clear();
    assert!(simulator::stream(&c, Templates::load(None).unwrap(), 42, 48).is_err());
    c = Config::load(None).unwrap();
    c.guitar.phrases_per_region = 0;
    assert!(simulator::stream(&c, Templates::load(None).unwrap(), 42, 48).is_err());
    c = Config::load(None).unwrap();
    c.simulation.seventh_probability = f64::NAN;
    assert!(simulator::stream(&c, Templates::load(None).unwrap(), 42, 48).is_err());
    c = Config::load(None).unwrap();
    for base in [0, 23, 73, 255] {
        assert!(simulator::stream(&c, Templates::load(None).unwrap(), 42, base).is_err());
    }
}
