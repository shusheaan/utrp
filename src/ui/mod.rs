mod compact;
pub mod footer;
pub mod guitar;
pub mod header;
pub mod notation;
pub mod piano;
pub mod progression;
pub mod target;
use crate::app::App;
use ratatui::{
    layout::{Constraint, Direction, Layout},
    Frame,
};

pub fn render(frame: &mut Frame, app: &mut App) {
    let area = frame.area();
    let instrument_width = if app.instrument == "guitar" { 48 } else { 61 };
    let staff_height = notation::required_height(app);
    let staff_width = notation::panel_width(app);
    if area.width < staff_width + instrument_width || area.height < staff_height + 16 {
        compact::render(frame, app);
        return;
    }
    app.view_scroll = 0;
    app.view_max_scroll = 0;
    let panel_height = staff_height.max(12);
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(2),
            Constraint::Min(6),
            Constraint::Length(4),
            Constraint::Length(panel_height),
            Constraint::Length(2),
        ])
        .split(area);
    header::render(frame, app, chunks[0]);
    progression::render(frame, app, chunks[1]);
    target::render(frame, app, chunks[2]);
    let panels = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Length(staff_width),
            Constraint::Min(instrument_width),
        ])
        .split(chunks[3]);
    notation::render(frame, app, panels[0]);
    let instrument_area = panels[1];
    if app.instrument == "guitar" {
        guitar::render(frame, app, instrument_area);
    } else {
        piano::render(frame, app, instrument_area);
    }
    footer::render(frame, app, chunks[4]);
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::{backend::TestBackend, Terminal};
    use utrp::{
        config::{Config, Templates},
        session::Session,
        simulator,
    };
    fn scroll_text(terminal: &mut Terminal<TestBackend>, app: &mut App) -> String {
        app.view_scroll = 0;
        terminal.draw(|f| render(f, app)).unwrap();
        let mut text = String::new();
        let max_scroll = app.view_max_scroll;
        for offset in 0..=max_scroll {
            app.view_scroll = offset;
            terminal.draw(|f| render(f, app)).unwrap();
            let buffer = terminal.backend().buffer();
            for row in buffer.content.chunks(usize::from(buffer.area.width)) {
                text.extend(row.iter().map(|cell| cell.symbol()));
            }
        }
        app.view_scroll = 0;
        text
    }

    #[test]
    fn existing_panel_layout_and_controls_render() {
        let c = Config::load(None).unwrap();
        let s = Session::new(
            simulator::stream(&c, Templates::load(None).unwrap(), 42, 48).unwrap(),
            c.session,
            0,
        );
        let mut app = App::new(s, "guitar".into(), None, None);
        let mut terminal = Terminal::new(TestBackend::new(120, 50)).unwrap();
        terminal.draw(|f| render(f, &mut app)).unwrap();
        let buf = terminal.backend().buffer();
        let text = buf
            .content
            .iter()
            .map(|cell| cell.symbol())
            .collect::<String>();
        for label in [
            "U-TR-P",
            "Progression",
            "Guitar",
            "Chord tones",
            "Space found",
            "Tab auto/manual",
            "MANUAL",
            "unlimited",
            "Enter stop",
            "[current] -> next",
        ] {
            assert!(text.contains(label), "missing {label}");
        }
        let footer = buf
            .content
            .chunks(120)
            .last()
            .unwrap()
            .iter()
            .map(|cell| cell.symbol())
            .collect::<String>();
        assert!(footer.contains("Tab auto/manual"), "{footer}");
    }
    #[test]
    fn minimum_supported_size_keeps_action_feedback_visible() {
        for instrument in ["guitar", "piano"] {
            let mut c = Config::load(None).unwrap();
            // Longest configured backbone chunks, with every eligible target
            // receiving a two-chord approach; current target/feedback must fit.
            c.simulation.cycle_chunk_size = 8;
            c.simulation.secondary_probability = 0.0;
            c.simulation.substitution_probability = 0.0;
            c.simulation.borrow_probability = 0.0;
            c.simulation.sd25_probability = 0.0;
            c.simulation.ssd25_probability = 1.0;
            let session = Session::new(
                simulator::stream(&c, Templates::load(None).unwrap(), 42, 48).unwrap(),
                c.session,
                0,
            );
            let mut app = App::new(session, instrument.into(), None, None);
            app.notice = "FOUND: self-reported +1".into();
            let mut terminal = Terminal::new(TestBackend::new(72, 30)).unwrap();
            for _ in 0..1000 {
                terminal.draw(|f| render(f, &mut app)).unwrap();
                let text = terminal
                    .backend()
                    .buffer()
                    .content
                    .iter()
                    .map(|cell| cell.symbol())
                    .collect::<String>();
                assert!(text.contains(&app.notice), "{instrument}: {text}");
                assert!(
                    text.contains(&format!(":{}]", app.session.target().music.chord.symbol())),
                    "current chord hidden: {text}"
                );
                let id = app.session.target().music.id;
                app.session.apply(utrp::session::Action::Next, 0, id);
            }
        }
    }
    #[test]
    fn manual_pending_and_controls_fit_minimum_terminal() {
        use utrp::session::Action;
        let mut c = Config::load(None).unwrap();
        c.simulation.approaches = false;
        let s = Session::new(
            simulator::stream(&c, Templates::load(None).unwrap(), 42, 48).unwrap(),
            c.session,
            0,
        );
        let mut app = App::new(s, "guitar".into(), None, None);
        let mut terminal = Terminal::new(TestBackend::new(72, 30)).unwrap();
        app.session.apply(Action::ModulateBalanced, 0, 0);
        for expected in ["NEXT", "CURRENT"] {
            let text = scroll_text(&mut terminal, &mut app);
            for label in [
                "Tab auto/manual",
                "E random",
                "Q back",
                "Enter stop",
                "Space found",
                &format!("Pending E balanced: after {expected}"),
                &app.notice,
            ] {
                assert!(text.contains(label), "missing {label}: {text}");
            }
            let id = app.session.target().music.id;
            app.session.apply(Action::Next, 0, id);
        }
        terminal.draw(|f| render(f, &mut app)).unwrap();
        let text: String = terminal
            .backend()
            .buffer()
            .content
            .iter()
            .map(|cell| cell.symbol())
            .collect();
        assert!(text.contains("Manual E:"));
        assert!(!text.contains("Pending E"));
    }
    #[test]
    fn small_terminal_shows_content_and_scroll_hint() {
        let c = Config::load(None).unwrap();
        let s = Session::new(
            simulator::stream(&c, Templates::load(None).unwrap(), 42, 48).unwrap(),
            c.session,
            0,
        );
        let mut app = App::new(s, "guitar".into(), None, None);
        let mut terminal = Terminal::new(TestBackend::new(40, 10)).unwrap();
        terminal.draw(|f| render(f, &mut app)).unwrap();
        assert!(terminal
            .backend()
            .buffer()
            .content
            .iter()
            .map(|c| c.symbol())
            .collect::<String>()
            .contains("j/k scroll"));
    }

    #[test]
    fn phone_scrolling_exposes_all_panels_and_full_details() {
        fn compact(text: &str) -> String {
            text.chars().filter(|c| !c.is_whitespace()).collect()
        }
        for instrument in ["guitar", "piano"] {
            let c = Config::load(None).unwrap();
            let s = Session::new(
                simulator::stream(&c, Templates::load(None).unwrap(), 42, 48).unwrap(),
                c.session,
                0,
            );
            let mut app = App::new(s, instrument.into(), None, None);
            for (width, height) in [(20, 10), (32, 24), (40, 20), (60, 24), (72, 30)] {
                let mut terminal = Terminal::new(TestBackend::new(width, height)).unwrap();
                for _ in 0..8 {
                    let text = compact(&scroll_text(&mut terminal, &mut app));
                    for label in [
                        "U-TR-P",
                        "Progression",
                        "Scale:",
                        "Chord tones",
                        "Staff | concert pitch",
                        "C4",
                        "Enter stop",
                        "Tab auto/manual",
                        "Found=self-report; skipped/timeout=no credit",
                    ] {
                        assert!(text.contains(&compact(label)), "{width}x{height}: {label}");
                    }
                    let mut expected = progression::compact_lines(&app);
                    expected.extend(target::lines(&app));
                    if instrument == "guitar" {
                        expected.extend(guitar::lines(&app));
                    } else {
                        expected.extend(piano::compact_lines(&app, width));
                    }
                    for line in expected {
                        let line = compact(&line.to_string());
                        // Long phrases can span more than one viewport; individual
                        // events are checked below instead of the whole phrase.
                        if line.contains("->") && line.contains('[') {
                            continue;
                        }
                        assert!(text.contains(&line), "{instrument} {width}: missing {line}");
                    }
                    for event in app.session.phrase_events() {
                        assert!(text.contains(&compact(&event.chord.symbol())));
                    }
                    assert!(!text.contains("Resizestaff"));
                    let id = app.session.target().music.id;
                    app.session.apply(utrp::session::Action::Next, 0, id);
                }
            }
        }
    }

    #[test]
    fn resizing_and_tiny_viewports_clamp_scroll_without_panicking() {
        let c = Config::load(None).unwrap();
        let s = Session::new(
            simulator::stream(&c, Templates::load(None).unwrap(), 42, 48).unwrap(),
            c.session,
            0,
        );
        let mut app = App::new(s, "guitar".into(), None, None);
        for (width, height) in [(40, 10), (32, 24), (120, 50), (20, 60), (1, 1), (0, 0)] {
            app.view_scroll = u16::MAX;
            let mut terminal = Terminal::new(TestBackend::new(width, height)).unwrap();
            terminal.draw(|f| render(f, &mut app)).unwrap();
            if width > 0 && height > 0 {
                assert!(app.view_scroll <= app.view_max_scroll);
                if width == 120 {
                    assert_eq!(app.view_scroll, 0);
                }
            }
        }
    }

    #[test]
    fn full_layout_renders_staff_and_text_without_cropping_over_many_targets() {
        let c = Config::load(None).unwrap();
        let session = Session::new(
            simulator::stream(&c, Templates::load(None).unwrap(), 42, 48).unwrap(),
            c.session,
            0,
        );
        let mut app = App::new(session, "guitar".into(), None, None);
        let mut terminal = Terminal::new(TestBackend::new(120, 50)).unwrap();
        for _ in 0..100 {
            terminal.draw(|f| render(f, &mut app)).unwrap();
            let text = terminal
                .backend()
                .buffer()
                .content
                .iter()
                .map(|cell| cell.symbol())
                .collect::<String>();
            for label in [
                "Staff | concert pitch",
                "C4",
                "Guitar",
                "Chord tones",
                "Enter stop",
            ] {
                assert!(text.contains(label), "missing {label}");
            }
            assert!(!text.contains("Resize staff"));
            let id = app.session.target().music.id;
            app.session.apply(utrp::session::Action::Next, 0, id);
        }
    }
}
