use std::collections::BTreeSet;
use utrp::{
    config::{Config, Templates},
    session::{Action, Session},
    simulator,
    theory::tone::Tone,
};

#[test]
fn phrase_preview_never_advances_generator_or_counts_unpresented_targets() {
    let config = Config::load(None).unwrap();
    let stream = simulator::stream(&config, Templates::load(None).unwrap(), 42, 48).unwrap();
    let mut session = Session::new(stream, config.session, 0);
    let expected: Vec<_> = session.phrase_events().into_iter().cloned().collect();
    assert!(expected.len() > 1);
    for _ in 0..100 {
        assert_eq!(
            session
                .phrase_events()
                .into_iter()
                .cloned()
                .collect::<Vec<_>>(),
            expected
        );
    }
    assert_eq!(session.summary(0).presented, 1);
    assert_eq!(session.summary(0).score, 0);
    for event in &expected {
        assert_eq!(session.target().music, *event);
        session.apply(Action::Next, 1, event.id);
    }
    assert_eq!(session.target().music.phrase, expected[0].phrase + 1);
    let id = session.target().music.id;
    session.apply(Action::Previous, 2, id);
    assert_eq!(
        session
            .phrase_events()
            .into_iter()
            .cloned()
            .collect::<Vec<_>>(),
        expected
    );
}

#[test]
fn every_builtin_mode_template_covers_every_scale_degree() {
    for template in Templates::load(None).unwrap().templates {
        let seen: BTreeSet<_> = template.phrases.iter().flatten().copied().collect();
        assert_eq!(seen, (1..=7).collect(), "{}", template.mode.name());
    }
}

#[test]
fn scientific_spelling_respects_accidental_octave_boundaries() {
    for (spelling, midi, expected) in [
        ("C", 60, "C4"),
        ("B#", 60, "B#3"),
        ("Cb", 59, "Cb4"),
        ("Cbb", 58, "Cbb4"),
        ("B##", 61, "B##3"),
        ("F#", 66, "F#4"),
    ] {
        assert_eq!(Tone::parse(spelling).unwrap().midi_label(midi), expected);
    }
}

#[test]
fn restricted_pool_reports_missing_modulation_path_instead_of_faking_a_bridge() {
    let mut config = Config::load(None).unwrap();
    config.simulation.keys = vec!["C".into(), "D".into()];
    config.simulation.modes = vec![utrp::theory::key::Mode::Dorian];
    config.simulation.modulation_probability = 1.0;
    config.simulation.extensions = false;
    config.simulation.approaches = false;
    config.simulation.ambient = false;
    let mut stream = simulator::stream(&config, Templates::load(None).unwrap(), 42, 48).unwrap();
    let key = stream.next_target().music.key;
    let mut explained = false;
    for _ in 0..100 {
        let event = stream.next_target().music;
        assert_eq!(event.key, key);
        explained |= event.reason.starts_with("No supported modulation path");
    }
    assert!(explained);
}

#[test]
fn guitar_export_uses_actual_detached_path_not_hidden_grip() {
    let mut config = Config::load(None).unwrap();
    config.guitar.arpeggio_every = 1;
    let mut stream = simulator::stream(&config, Templates::load(None).unwrap(), 42, 48).unwrap();
    let mut target = stream.next_target();
    assert_eq!(target.guitar.task, "arpeggio_detached");
    let notes: Vec<_> = target.guitar.arpeggio.iter().map(|p| p.midi).collect();
    assert_eq!(
        simulator::export(&target, "guitar")["chords"][0]["notes"],
        serde_json::json!(notes)
    );
    target.guitar.arpeggio.pop();
    assert_eq!(
        simulator::export(&target, "guitar")["chords"][0]["notes"],
        serde_json::json!([])
    );
}
