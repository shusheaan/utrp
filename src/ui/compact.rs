use super::{footer, guitar, header, notation, piano, progression, target};
use crate::app::App;
use ratatui::{
    layout::Rect,
    style::{Color, Style},
    text::Line,
    widgets::{Paragraph, Wrap},
    Frame,
};

fn document(app: &App, width: u16) -> Paragraph<'static> {
    let mut lines = vec![header::line(app)];
    lines.extend(target::lines(app));
    lines.extend(progression::compact_lines(app));
    lines.push(Line::default());
    lines.extend(notation::compact_lines(app, width));
    lines.push(Line::default());
    if app.instrument == "guitar" {
        lines.push(Line::from("Guitar | string 1=highest, 6=lowest"));
        lines.extend(guitar::lines(app));
    } else {
        lines.extend(piano::compact_lines(app, width));
    }
    lines.extend(footer::lines());
    Paragraph::new(lines).wrap(Wrap { trim: false })
}

pub(super) fn render(frame: &mut Frame, app: &mut App) {
    let area = frame.area();
    if area.width == 0 || area.height == 0 {
        return;
    }
    // Reserve a persistent current target and a discoverable scroll control.
    let body = Rect::new(
        area.x,
        area.y + 1,
        area.width,
        area.height.saturating_sub(2),
    );
    let content = document(app, area.width);
    let total = content.line_count(area.width);
    app.view_max_scroll = total.saturating_sub(usize::from(body.height)) as u16;
    app.view_height = body.height;
    app.view_scroll = app.view_scroll.min(app.view_max_scroll);
    frame.render_widget(content.scroll((app.view_scroll, 0)), body);
    frame.render_widget(
        Paragraph::new(format!(
            "PLAY {}",
            app.session.target().music.chord.symbol()
        ))
        .style(Style::default().fg(Color::Yellow)),
        Rect::new(area.x, area.y, area.width, 1),
    );
    if area.height > 1 {
        frame.render_widget(
            Paragraph::new(format!(
                "j/k scroll {}/{}",
                app.view_scroll + 1,
                app.view_max_scroll + 1
            ))
            .style(Style::default().fg(Color::Cyan)),
            Rect::new(area.x, area.bottom() - 1, area.width, 1),
        );
    }
}
