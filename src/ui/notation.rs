use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

use crate::app::{App, GamePhase};
use crate::tone::Tone;
use crate::ui::strip_ansi;

/// Staff row indices (top to bottom, 0-based):
///  0: space above line 5 (G5 — not used in our mapping)
///  1: Line 5 (F5 — not used)
///  2: space (E5 — not used)
///  3: Line 4 (D5 — not used)
///  4: space (C5 — not used)
///  5: Line 3 (B4)
///  6: space (A4)
///  7: Line 2 (G4)
///  8: space (F4)
///  9: Line 1 (E4)
/// 10: space (D4)
/// 11: ledger line (C4)
const TOTAL_ROWS: usize = 12;

/// Map the first character of the tone's display string to a staff row.
fn note_letter_to_row(letter: char) -> Option<usize> {
    match letter {
        'C' => Some(11),
        'D' => Some(10),
        'E' => Some(9),
        'F' => Some(8),
        'G' => Some(7),
        'A' => Some(6),
        'B' => Some(5),
        _ => None,
    }
}

/// Whether a given row is a staff line (as opposed to a space or the ledger).
fn is_staff_line(row: usize) -> bool {
    matches!(row, 1 | 3 | 5 | 7 | 9)
}

/// Extract the tones to display from the current game phase.
fn get_target_tones(app: &App) -> Vec<Tone> {
    match &app.phase {
        GamePhase::WaitingForInput { target } => target.tones.clone(),
        GamePhase::Matched { chord } => chord.tones.clone(),
        _ => Vec::new(),
    }
}

/// Determine the note colour based on game phase.
fn note_color(app: &App) -> Color {
    match &app.phase {
        GamePhase::WaitingForInput { .. } => Color::Yellow,
        GamePhase::Matched { .. } => Color::Green,
        _ => Color::White,
    }
}

/// Build the display label for a tone (e.g. "C", "F#", "Bb").
fn tone_label(tone: &Tone) -> String {
    strip_ansi(&format!("{}", tone))
}

pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    let block = Block::default()
        .title(" Staff ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::DarkGray));
    let inner = block.inner(area);

    let tones = get_target_tones(app);
    let color = note_color(app);

    // Build a lookup: row -> label string for each tone present.
    let mut row_labels: Vec<Option<String>> = vec![None; TOTAL_ROWS];
    for tone in &tones {
        let label = tone_label(tone);
        if let Some(first_char) = label.chars().next() {
            if let Some(row) = note_letter_to_row(first_char) {
                row_labels[row] = Some(label);
            }
        }
    }

    // The usable width inside the border (in columns).
    let width = inner.width as usize;

    let line_style = Style::default().fg(Color::DarkGray);
    let note_style = Style::default()
        .fg(color)
        .add_modifier(Modifier::BOLD);

    let mut lines: Vec<Line<'static>> = Vec::with_capacity(TOTAL_ROWS);

    for row in 0..TOTAL_ROWS {
        let has_note = row_labels[row].is_some();
        let label = row_labels[row].clone().unwrap_or_default();

        let line = if row == 11 {
            // Ledger line row (C4): only draw a short ledger line if note is present.
            if has_note {
                build_ledger_line(width, &label, note_style, line_style)
            } else {
                // Empty row below the staff.
                Line::from(Span::styled(" ".repeat(width), Style::default()))
            }
        } else if is_staff_line(row) {
            // Full staff line.
            build_staff_line(width, has_note, &label, note_style, line_style)
        } else {
            // Space row.
            build_space_row(width, has_note, &label, note_style)
        };

        lines.push(line);
    }

    let paragraph = Paragraph::new(lines).block(block);
    frame.render_widget(paragraph, area);
}

/// Build a full staff line, optionally with a note marker in the centre.
fn build_staff_line(
    width: usize,
    has_note: bool,
    label: &str,
    note_style: Style,
    line_style: Style,
) -> Line<'static> {
    if width < 3 {
        return Line::from(Span::styled(
            "\u{2501}".repeat(width),
            line_style,
        ));
    }

    if !has_note {
        // Plain staff line: ━━━━━━━━━━━━
        return Line::from(Span::styled(
            "\u{2501}".repeat(width),
            line_style,
        ));
    }

    // Staff line with note: ━━━━ ●Lb ━━━━
    // The marker section is " ●{label} " (with surrounding spaces for readability).
    let marker = format!(" \u{25CF}{} ", label);
    let marker_len = marker.chars().count();

    if marker_len >= width {
        // Too narrow — just show the marker.
        return Line::from(Span::styled(marker, note_style));
    }

    let remaining = width - marker_len;
    let left = remaining / 2;
    let right = remaining - left;

    Line::from(vec![
        Span::styled("\u{2501}".repeat(left), line_style),
        Span::styled(marker, note_style),
        Span::styled("\u{2501}".repeat(right), line_style),
    ])
}

/// Build a space row (between staff lines), optionally with a note marker.
fn build_space_row(
    width: usize,
    has_note: bool,
    label: &str,
    note_style: Style,
) -> Line<'static> {
    if !has_note {
        return Line::from(Span::raw(" ".repeat(width)));
    }

    let marker = format!(" \u{25CF}{} ", label);
    let marker_len = marker.chars().count();

    if marker_len >= width {
        return Line::from(Span::styled(marker, note_style));
    }

    let remaining = width - marker_len;
    let left = remaining / 2;
    let right = remaining - left;

    Line::from(vec![
        Span::raw(" ".repeat(left)),
        Span::styled(marker, note_style),
        Span::raw(" ".repeat(right)),
    ])
}

/// Build a ledger line row for C4.
fn build_ledger_line(
    width: usize,
    label: &str,
    note_style: Style,
    line_style: Style,
) -> Line<'static> {
    // Short ledger line centred: "    ━━●C━━    "
    let marker = format!("\u{25CF}{}", label);
    let marker_len = marker.chars().count();

    // Ledger line extends 3 chars each side of the marker.
    let ledger_each_side: usize = 3;
    let ledger_total = marker_len + ledger_each_side * 2;

    if ledger_total >= width {
        // Too narrow — just draw ledger and marker.
        return Line::from(vec![
            Span::styled("\u{2501}".repeat(ledger_each_side), line_style),
            Span::styled(marker, note_style),
            Span::styled("\u{2501}".repeat(ledger_each_side), line_style),
        ]);
    }

    let remaining = width - ledger_total;
    let pad_left = remaining / 2;
    let pad_right = remaining - pad_left;

    Line::from(vec![
        Span::raw(" ".repeat(pad_left)),
        Span::styled("\u{2501}".repeat(ledger_each_side), line_style),
        Span::styled(marker, note_style),
        Span::styled("\u{2501}".repeat(ledger_each_side), line_style),
        Span::raw(" ".repeat(pad_right)),
    ])
}
