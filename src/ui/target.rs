use crate::app::App;
use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};
pub(super) fn lines(app: &App) -> Vec<Line<'static>> {
    let target = app.session.target();
    let remaining = app
        .session
        .remaining_ms(app.now)
        .map_or("unlimited".into(), |n| {
            format!("{:.1}s left", n as f64 / 1000.0)
        });
    let history = if app.session.attempts[app.session.index].is_some() {
        " | REVIEW (no credit)"
    } else {
        ""
    };
    let task = if app.instrument != "guitar" {
        "MIDI exact notes"
    } else if target.guitar.task == "arpeggio_detached" {
        "DETACHED"
    } else {
        "CHORD"
    };
    let chord = &target.music.chord;
    let tones = chord
        .tones
        .iter()
        .enumerate()
        .map(|(i, tone)| format!("{}:{}", chord.degree_label(i), tone.name))
        .collect::<Vec<_>>()
        .join("  ");
    vec![
        Line::from(vec![
            Span::styled(
                "  >> PLAY ",
                Style::default()
                    .fg(Color::Yellow)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled(
                chord.symbol(),
                Style::default()
                    .fg(Color::White)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::raw(format!(" | {remaining} | {task}{history}")),
        ]),
        Line::from(Span::styled(
            format!("  Chord tones: {tones}"),
            Style::default().fg(Color::Green),
        )),
    ]
}

pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    frame.render_widget(
        Paragraph::new(lines(app)).block(
            Block::default()
                .borders(Borders::TOP | Borders::BOTTOM)
                .border_style(Style::default().fg(Color::DarkGray)),
        ),
        area,
    );
}
