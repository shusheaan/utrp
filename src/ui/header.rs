use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};
use crate::app::App;

pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    let elapsed = app.elapsed_secs();
    let mins = elapsed / 60;
    let secs = elapsed % 60;

    let line = Line::from(vec![
        Span::styled(
            " U-TR-P ",
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled("v0.2.1 ", Style::default().fg(Color::DarkGray)),
        Span::raw(" | "),
        Span::styled("Score: ", Style::default().fg(Color::White)),
        Span::styled(
            format!("{}", app.score),
            Style::default()
                .fg(Color::Blue)
                .add_modifier(Modifier::BOLD),
        ),
        Span::raw(" | "),
        Span::styled("Time: ", Style::default().fg(Color::White)),
        Span::styled(
            format!("{:02}:{:02}", mins, secs),
            Style::default().fg(Color::Green),
        ),
        Span::raw(" | "),
        Span::styled(
            format!("Measure: {}/100", app.measure_num),
            Style::default().fg(Color::DarkGray),
        ),
    ]);

    let block = Block::default()
        .borders(Borders::BOTTOM)
        .border_style(Style::default().fg(Color::DarkGray));
    let paragraph = Paragraph::new(line).block(block);
    frame.render_widget(paragraph, area);
}
