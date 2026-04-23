use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};
use crate::app::App;
use super::strip_ansi;

pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    let mut lines: Vec<Line> = Vec::new();

    let current_key = strip_ansi(&format!("{}", app.current.key));
    let current_chord = if !app.current.chords.is_empty() {
        strip_ansi(&format!("{}", app.current.chords[0]))
    } else {
        String::new()
    };
    let modulation = strip_ansi(&format!("{}", app.modulation));
    let next_key = strip_ansi(&format!("{}", app.next.key));

    lines.push(Line::from(vec![
        Span::styled("  Current: ", Style::default().fg(Color::White)),
        Span::styled(
            &*current_key,
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        ),
        Span::raw("  "),
        Span::styled(&*current_chord, Style::default().fg(Color::Green)),
    ]));

    lines.push(Line::from(vec![Span::styled(
        format!("  {}", modulation),
        Style::default().fg(Color::Yellow),
    )]));

    lines.push(Line::from(""));

    lines.push(Line::from(vec![
        Span::styled("  => ", Style::default().fg(Color::Cyan)),
        Span::styled(
            format!("{}:", next_key),
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        ),
    ]));

    let chords = &app.next.chords;
    let depth = chords.len();
    for i in (0..depth).rev() {
        let indent = "  ".repeat(depth - i);
        let arrows: String = (0..(depth - i)).map(|_| "->").collect::<Vec<_>>().join("");
        let chord_str = strip_ansi(&format!("{}", chords[i]));
        lines.push(Line::from(vec![
            Span::raw(format!("  {}", indent)),
            Span::styled(
                format!("{} ", arrows),
                Style::default().fg(Color::DarkGray),
            ),
            Span::styled(
                chord_str,
                Style::default()
                    .fg(Color::White)
                    .add_modifier(Modifier::BOLD),
            ),
        ]));
    }

    let block = Block::default()
        .title(" Progression ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::DarkGray));
    let paragraph = Paragraph::new(lines).block(block);
    frame.render_widget(paragraph, area);
}
