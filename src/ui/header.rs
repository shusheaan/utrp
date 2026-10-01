use crate::app::App;
use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};
pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    let s = app.session.summary(app.now);
    let secs = s.elapsed_ms / 1000;
    let line = Line::from(vec![
        Span::styled(
            " U-TR-P ",
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(
            format!("{} | ", app.instrument),
            Style::default().fg(Color::DarkGray),
        ),
        Span::styled(
            format!(
                "Score: {}  Found: {} ",
                s.score,
                s.confirmed + s.midi_matched
            ),
            Style::default().fg(Color::Blue),
        ),
        Span::styled(
            format!("| {:02}:{:02} ", secs / 60, secs % 60),
            Style::default().fg(Color::Green),
        ),
        Span::styled(
            format!(
                "| #{}  {:.1}s/chord {}",
                app.session.index + 1,
                app.session.seconds,
                if app.session.paused {
                    "PAUSED"
                } else if app.session.automatic {
                    "AUTO"
                } else {
                    "MANUAL"
                }
            ),
            Style::default().fg(Color::Yellow),
        ),
    ]);
    frame.render_widget(
        Paragraph::new(line).block(
            Block::default()
                .borders(Borders::BOTTOM)
                .border_style(Style::default().fg(Color::DarkGray)),
        ),
        area,
    );
}
