use crate::app::App;
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph, Wrap},
    Frame,
};
use utrp::progression::ChordEvent;

fn event_label(event: &ChordEvent) -> String {
    let label = match event.role.as_str() {
        "bridge" if event.reason.starts_with("Return: ") => "V7/back".into(),
        "bridge" => "V7/new".into(),
        "shared_pivot" => format!("pivot/{}", event.degree.expect("pivot degree")),
        "diminished_pivot" => "dim7/new".into(),
        "minor_dominant" => "V7/i".into(),
        "secondary" => "V7/target".into(),
        "substitute" => "subV".into(),
        "sd25_ii" => "ii/target".into(),
        "sd25_v" => "V7/target".into(),
        "ssd25_ii" => "ii/subV".into(),
        "ssd25_v" => "subV/target".into(),
        "borrowed" => "iv(borrow)".into(),
        _ => event.degree.map_or("-".into(), |degree| degree.to_string()),
    };
    format!("{label}:{}", event.chord.symbol())
}

fn role_description(event: &ChordEvent) -> &str {
    if event.reason.starts_with("Return: ") {
        return "Return to previous key via a prepared transition";
    }
    if event.reason.starts_with("No supported modulation path") {
        return "No supported modulation path in pool; staying in current key";
    }
    match event.role.as_str() {
        "shared_pivot" | "diminished_pivot" => &event.reason,
        "sd25_ii" | "sd25_v" | "ssd25_ii" | "ssd25_v" => &event.reason,
        "minor_dominant" => "Minor V7 -> i: raised leading tone; no key change",
        "bridge" => "Prepare the new tonic: dominant seventh -> tonic",
        "secondary" => "Secondary dominant -> target; current key stays the same",
        "substitute" => "Tritone substitute -> target; current key stays the same",
        "borrowed" => "Borrowed minor iv -> I; current key stays the same",
        "arrival" => "New tonic reached; continue the phrase in this key",
        "mode_change" => "Same tonic, different mode",
        _ if event.cycle.is_some() => "Original cycle: auto changes at end; E/Q may interrupt",
        _ => "In-key phrase / color; keep the tonal center",
    }
}

fn phrase_line(events: &[&ChordEvent], current_id: usize) -> Line<'static> {
    let mut spans = vec![Span::raw("  ")];
    for (i, event) in events.iter().enumerate() {
        if i > 0 {
            spans.push(Span::styled(" -> ", Style::default().fg(Color::DarkGray)));
        }
        let label = event_label(event);
        spans.push(if event.id == current_id {
            Span::styled(
                format!("[{label}]"),
                Style::default()
                    .fg(Color::Yellow)
                    .add_modifier(Modifier::BOLD),
            )
        } else {
            Span::styled(
                label,
                Style::default().fg(if event.id < current_id {
                    Color::DarkGray
                } else {
                    Color::White
                }),
            )
        });
    }
    Line::from(spans)
}

/// Wrap at event boundaries, then keep the current event's row in view.
/// Unlike clipping one long Paragraph, this never hides the active chord.
fn phrase_window(
    events: &[&ChordEvent],
    current_id: usize,
    width: u16,
    height: u16,
) -> Vec<Line<'static>> {
    if events.is_empty() || height == 0 {
        return Vec::new();
    }
    let mut rows = Vec::new();
    let mut start = 0;
    let mut current_row = 0;
    for end in 1..=events.len() {
        if end > start + 1
            && phrase_line(&events[start..end], current_id).width() > usize::from(width)
        {
            if events[start..end - 1].iter().any(|e| e.id == current_id) {
                current_row = rows.len();
            }
            rows.push(phrase_line(&events[start..end - 1], current_id));
            start = end - 1;
        }
    }
    if events[start..].iter().any(|e| e.id == current_id) {
        current_row = rows.len();
    }
    rows.push(phrase_line(&events[start..], current_id));
    let height = usize::from(height);
    let offset = current_row
        .saturating_sub((height - 1) / 2)
        .min(rows.len().saturating_sub(height));
    let hidden_after = rows.len() > offset + height;
    let mut visible: Vec<_> = rows.into_iter().skip(offset).take(height).collect();
    if offset > 0 {
        visible[0].spans[0] = Span::raw("< ");
    }
    if hidden_after {
        let last = visible.last_mut().expect("nonempty window");
        last.spans[0] = Span::raw(if offset > 0 && height == 1 {
            "<>"
        } else {
            "> "
        });
    }
    visible
}

pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    let event = &app.session.target().music;
    let phrase = app.session.phrase_events();
    let transition = phrase.iter().find_map(|e| e.previous_key.as_ref());
    let mut route = transition.map_or_else(
        || format!("Key: {} | stay in key", event.key.label()),
        |old| format!("Key: {} => {}", old.label(), event.key.label()),
    );
    if let Some(cycle) = &event.cycle {
        route.push_str(&format!(
            " | Cycle {} {}/{}",
            cycle.lap, cycle.step, cycle.total
        ));
    }
    let scale = event
        .key
        .scale()
        .iter()
        .enumerate()
        .map(|(i, tone)| format!("{}:{}", i + 1, tone.name))
        .collect::<Vec<_>>()
        .join("  ");
    let block = Block::default()
        .title(format!(
            " Progression | phrase {} | [current] -> next ",
            event.phrase + 1
        ))
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::DarkGray));
    let inner = block.inner(area);
    frame.render_widget(block, area);
    let slots = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(1),
            Constraint::Length(1),
            Constraint::Min(1),
            Constraint::Length(2),
            Constraint::Length(1),
        ])
        .split(inner);
    let lines = [
        Line::from(Span::styled(
            format!("  {route}"),
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(Span::styled(
            format!("  Scale: {scale}"),
            Style::default().fg(Color::DarkGray),
        )),
        Line::from(Span::styled(
            format!("  {}", role_description(event)),
            Style::default().fg(Color::Green),
        )),
        Line::from(Span::styled(
            format!("  {}", app.notice),
            Style::default().fg(Color::DarkGray),
        )),
    ];
    for (line, slot) in lines
        .into_iter()
        .zip([slots[0], slots[1], slots[3], slots[4]])
    {
        frame.render_widget(Paragraph::new(line).wrap(Wrap { trim: false }), slot);
    }
    render_manual_status(frame, app, slots[3]);
    frame.render_widget(
        Paragraph::new(phrase_window(
            &phrase,
            event.id,
            slots[2].width,
            slots[2].height,
        )),
        slots[2],
    );
}

fn render_manual_status(frame: &mut Frame, app: &App, area: Rect) {
    let event = &app.session.target().music;
    let status = app
        .session
        .pending_manual_label()
        .unwrap_or_else(|| app.session.manual_notice().into());
    if !status.is_empty() {
        frame.render_widget(
            Paragraph::new(vec![
                Line::from(Span::styled(
                    format!("  {}", role_description(event)),
                    Style::default().fg(Color::Green),
                )),
                Line::from(Span::styled(
                    format!("  {status}"),
                    Style::default().fg(Color::Cyan),
                )),
            ]),
            area,
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use utrp::{
        config::{Config, Templates},
        progression::Progression,
    };

    #[test]
    fn migrated_routes_and_return_have_distinct_readable_labels() {
        let mut config = Config::load(None).unwrap();
        config.simulation.modulation_probability = 1.0;
        let mut engine =
            Progression::new(config.simulation, Templates::load(None).unwrap(), 42).unwrap();
        let mut seen = [false; 3];
        for _ in 0..6000 {
            let event = engine.next_event();
            match event.role.as_str() {
                "shared_pivot" => {
                    assert!(event_label(&event).starts_with("pivot/"));
                    assert!(role_description(&event).contains("old "));
                    assert!(role_description(&event).contains(" = new "));
                    seen[0] = true;
                }
                "diminished_pivot" => {
                    assert!(event_label(&event).starts_with("dim7/new:"));
                    assert!(role_description(&event).contains("Dim7 chromatic:"));
                    seen[1] = true;
                }
                _ => {}
            }
            if event.reason.starts_with("Return: ") {
                assert!(role_description(&event).contains("Return to previous key"));
                if event.role == "bridge" {
                    assert!(event_label(&event).starts_with("V7/back:"));
                }
                seen[2] = true;
            }
        }
        assert_eq!(seen, [true; 3]);
    }
}
