pub mod header;
pub mod progression;
pub mod target;
pub mod piano;
pub mod guitar;
pub mod notation;
pub mod footer;

use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    Frame,
};
use crate::app::{App, Difficulty, GamePhase};

/// Strip ANSI escape codes from a string.
/// Needed because many types use the `colored` crate in their Display impl,
/// and those escape sequences break ratatui's layout calculations.
pub(crate) fn strip_ansi(s: &str) -> String {
    let mut result = String::new();
    let mut in_escape = false;
    for c in s.chars() {
        if c == '\x1b' {
            in_escape = true;
            continue;
        }
        if in_escape {
            if c == 'm' {
                in_escape = false;
            }
            continue;
        }
        result.push(c);
    }
    result
}

pub fn render(frame: &mut Frame, app: &App) {
    let area = frame.area();
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),
            Constraint::Min(8),
            Constraint::Length(3),
            Constraint::Length(12),
            Constraint::Length(1),
        ])
        .split(area);

    header::render(frame, app, chunks[0]);
    progression::render(frame, app, chunks[1]);
    target::render(frame, app, chunks[2]);

    let viz_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(30),
            Constraint::Percentage(70),
        ])
        .split(chunks[3]);

    notation::render(frame, app, viz_chunks[0]);

    match app.difficulty {
        Difficulty::Piano => piano::render(frame, app, viz_chunks[1]),
        Difficulty::Guitar => guitar::render(frame, app, viz_chunks[1]),
    }

    footer::render(frame, app, chunks[4]);
}
