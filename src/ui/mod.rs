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
    widgets::{Clear, Paragraph},
    Frame,
};

pub fn render(frame: &mut Frame, app: &App) {
    let area = frame.area();
    if area.width < 72 || area.height < 30 {
        frame.render_widget(Paragraph::new("U-TR-P: enlarge terminal to at least 72x30.\nEnter stop | Space found | WASD navigate/speed"),area);
        return;
    }
    let instrument_width = if app.instrument == "guitar" { 48 } else { 61 };
    let staff_height = notation::required_height(app);
    let full_staff =
        area.width >= notation::MIN_WIDTH + instrument_width && area.height >= staff_height + 16;
    let panel_height = if full_staff { staff_height.max(12) } else { 12 };
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
    let instrument_area = if full_staff {
        let panels = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Length(notation::MIN_WIDTH),
                Constraint::Min(instrument_width),
            ])
            .split(chunks[3]);
        notation::render(frame, app, panels[0]);
        panels[1]
    } else {
        chunks[3]
    };
    if app.instrument == "guitar" {
        guitar::render(frame, app, instrument_area);
    } else {
        piano::render(frame, app, instrument_area);
    }
    footer::render(frame, app, chunks[4]);
    if !full_staff {
        let hint = ratatui::layout::Rect::new(chunks[4].x, chunks[4].y + 1, chunks[4].width, 1);
        frame.render_widget(Clear, hint);
        frame.render_widget(
            Paragraph::new(format!(
                " P pause  M auto/manual | Full staff needs {}x{}; text view active",
                notation::MIN_WIDTH + instrument_width,
                staff_height + 16,
            ))
            .style(ratatui::style::Style::default().fg(ratatui::style::Color::DarkGray)),
            hint,
        );
    }
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
    #[test]
    fn existing_panel_layout_and_controls_render() {
        let c = Config::load(None).unwrap();
        let s = Session::new(
            simulator::stream(&c, Templates::load(None).unwrap(), 42, 48).unwrap(),
            c.session,
            0,
        );
        let app = App::new(s, "guitar".into(), None, None);
        let mut terminal = Terminal::new(TestBackend::new(120, 35)).unwrap();
        terminal.draw(|f| render(f, &app)).unwrap();
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
        assert!(footer.trim_end().ends_with("text view active"), "{footer}");
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
                terminal.draw(|f| render(f, &app)).unwrap();
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
            terminal.draw(|f| render(f, &app)).unwrap();
            let text: String = terminal
                .backend()
                .buffer()
                .content
                .iter()
                .map(|cell| cell.symbol())
                .collect();
            for label in [
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
        terminal.draw(|f| render(f, &app)).unwrap();
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
    fn small_terminal_is_explicit_and_does_not_panic() {
        let c = Config::load(None).unwrap();
        let s = Session::new(
            simulator::stream(&c, Templates::load(None).unwrap(), 42, 48).unwrap(),
            c.session,
            0,
        );
        let app = App::new(s, "guitar".into(), None, None);
        let mut terminal = Terminal::new(TestBackend::new(40, 10)).unwrap();
        terminal.draw(|f| render(f, &app)).unwrap();
        assert!(terminal
            .backend()
            .buffer()
            .content
            .iter()
            .map(|c| c.symbol())
            .collect::<String>()
            .contains("enlarge terminal"));
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
            terminal.draw(|f| render(f, &app)).unwrap();
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
