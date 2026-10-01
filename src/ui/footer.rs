use crate::app::App;
use ratatui::{
    layout::Rect,
    style::{Color, Style},
    text::{Line, Span},
    widgets::Paragraph,
    Frame,
};
pub fn render(frame: &mut Frame, _app: &App, area: Rect) {
    frame.render_widget(
        Paragraph::new(vec![
            Line::from(vec![
                Span::styled(
                    " W/S speed A/D prev/next E random Q back Space found ",
                    Style::default().fg(Color::Yellow),
                ),
                Span::styled(" Enter stop ", Style::default().fg(Color::Red)),
            ]),
            Line::from(Span::styled(
                " P pause  Tab auto/manual | Found=self-report; skipped/timeout=no credit",
                Style::default().fg(Color::DarkGray),
            )),
        ]),
        area,
    );
}
