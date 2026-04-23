use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};
use crate::app::{App, GamePhase};
use super::strip_ansi;

pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    let (label, label_color, chord_str) = match &app.phase {
        GamePhase::WaitingForInput { target } => {
            (">> PLAY", Color::Yellow, strip_ansi(&format!("{}", target)))
        }
        GamePhase::Matched { chord } => {
            ("** MATCHED", Color::Green, strip_ansi(&format!("{}", chord)))
        }
        GamePhase::MeasureTimeout => ("!! TIMEOUT", Color::Red, String::new()),
        GamePhase::GameTimeout => ("!! GAME OVER", Color::Red, String::new()),
        GamePhase::Score => ("   SCORE", Color::Blue, format!("{}", app.score)),
        GamePhase::Summary { duration_secs } => {
            let m = duration_secs / 60;
            let s = duration_secs % 60;
            (
                "== SUMMARY",
                Color::Cyan,
                format!("Time: {:02}:{:02}  Score: {}", m, s, app.score),
            )
        }
        GamePhase::Ready => ("-- GET READY", Color::Cyan, String::new()),
        GamePhase::Playing => (">> START", Color::Blue, String::new()),
        _ => ("", Color::White, String::new()),
    };

    let line = Line::from(vec![
        Span::styled(
            format!("  {} ", label),
            Style::default()
                .fg(label_color)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(
            chord_str,
            Style::default()
                .fg(Color::White)
                .add_modifier(Modifier::BOLD),
        ),
    ]);

    let block = Block::default()
        .borders(Borders::TOP | Borders::BOTTOM)
        .border_style(Style::default().fg(Color::DarkGray));
    let paragraph = Paragraph::new(line).block(block);
    frame.render_widget(paragraph, area);
}
