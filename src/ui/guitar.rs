use ratatui::{
    layout::Rect,
    style::{Color, Style},
    widgets::{Block, Borders},
    Frame,
};
use crate::app::App;

pub fn render(frame: &mut Frame, _app: &App, area: Rect) {
    let block = Block::default()
        .title(" Guitar ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::DarkGray));
    frame.render_widget(block, area);
}
