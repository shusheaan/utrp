use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::Paragraph,
    Frame,
};
use crate::app::App;

pub fn render(frame: &mut Frame, _app: &App, area: Rect) {
    let line = Line::from(vec![
        Span::styled(
            " [Enter]",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        ),
        Span::raw(" Skip  "),
        Span::styled(
            "[Q]",
            Style::default()
                .fg(Color::Red)
                .add_modifier(Modifier::BOLD),
        ),
        Span::raw(" Quit"),
    ]);
    let paragraph = Paragraph::new(line);
    frame.render_widget(paragraph, area);
}
