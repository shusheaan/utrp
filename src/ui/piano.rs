use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};
use crate::app::{App, GamePhase};
use crate::ui::strip_ansi;

/// White keys: (pitch class index, label)
const WHITE_KEYS: [(i8, &str); 7] = [
    (1, "C"),
    (3, "D"),
    (5, "E"),
    (6, "F"),
    (8, "G"),
    (10, "A"),
    (12, "B"),
];

/// Black keys in order, with their position as the index of the white key
/// to their LEFT (0-based).  E.g. C# sits between C(0) and D(1) -> left=0.
const BLACK_KEY_SLOTS: [(Option<(i8, &str)>, ); 7] = [
    (Some((2, "C#")),),  // between C and D
    (Some((4, "D#")),),  // between D and E
    (None,),             // between E and F  (no black key)
    (Some((7, "F#")),),  // between F and G
    (Some((9, "G#")),),  // between G and A
    (Some((11, "A#")),), // between A and B
    (None,),             // after B (gap to next octave)
];

const NUM_OCTAVES: usize = 3;

/// Collect the active pitch-class indices from the current game phase.
fn active_indices(app: &App) -> Vec<i8> {
    match &app.phase {
        GamePhase::WaitingForInput { target } => target.tones.iter().map(|t| t.idx).collect(),
        GamePhase::Matched { chord } => chord.tones.iter().map(|t| t.idx).collect(),
        _ => Vec::new(),
    }
}

/// Pick the highlight colour based on game phase.
fn active_color(app: &App) -> Color {
    match &app.phase {
        GamePhase::Matched { .. } => Color::Green,
        _ => Color::Yellow,
    }
}

/// Get a human-readable list of the chord's tone names.
fn get_tone_names(app: &App) -> String {
    match &app.phase {
        GamePhase::WaitingForInput { target } => target
            .tones
            .iter()
            .map(|t| strip_ansi(&format!("{}", t)))
            .collect::<Vec<_>>()
            .join(" "),
        GamePhase::Matched { chord } => chord
            .tones
            .iter()
            .map(|t| strip_ansi(&format!("{}", t)))
            .collect::<Vec<_>>()
            .join(" "),
        _ => String::new(),
    }
}

/// Build the spans for the black-key row (one line) across all octaves.
///
/// Each white-key column is 4 chars wide.  A black key label is placed
/// straddling the boundary between two white keys — specifically in the
/// 4-char slot that starts 2 chars before the boundary.  Gaps (no black
/// key) are filled with spaces.
fn build_black_row(active: &[i8], hi_color: Color) -> Vec<Span<'static>> {
    let mut spans: Vec<Span<'static>> = Vec::new();

    for oct in 0..NUM_OCTAVES {
        // Leading 2-char pad (left half of the first white key)
        spans.push(Span::raw("  ".to_string()));

        for slot in &BLACK_KEY_SLOTS {
            match slot.0 {
                Some((idx, label)) => {
                    if active.contains(&idx) {
                        spans.push(Span::styled(
                            " \u{2605}  ".to_string(),
                            Style::default()
                                .fg(hi_color)
                                .add_modifier(Modifier::BOLD),
                        ));
                    } else {
                        spans.push(Span::styled(
                            format!("{:^4}", label),
                            Style::default().fg(Color::White),
                        ));
                    }
                }
                None => {
                    spans.push(Span::raw("    ".to_string()));
                }
            }
        }

        // Trailing 2-char pad (right half of last white key)
        spans.push(Span::raw("  ".to_string()));
    }

    spans
}

/// Build the block-graphic row for black keys (solid blocks or stars).
fn build_black_block_row(active: &[i8], hi_color: Color) -> Vec<Span<'static>> {
    let mut spans: Vec<Span<'static>> = Vec::new();

    for _oct in 0..NUM_OCTAVES {
        spans.push(Span::raw("  ".to_string()));

        for slot in &BLACK_KEY_SLOTS {
            match slot.0 {
                Some((idx, _label)) => {
                    if active.contains(&idx) {
                        spans.push(Span::styled(
                            "\u{2588}\u{2605}\u{2605}\u{2588}".to_string(),
                            Style::default()
                                .fg(hi_color)
                                .add_modifier(Modifier::BOLD),
                        ));
                    } else {
                        spans.push(Span::styled(
                            "\u{2588}\u{2588}\u{2588}\u{2588}".to_string(),
                            Style::default().fg(Color::DarkGray),
                        ));
                    }
                }
                None => {
                    spans.push(Span::raw("    ".to_string()));
                }
            }
        }

        spans.push(Span::raw("  ".to_string()));
    }

    spans
}

/// Build the white-key label row across all octaves.
fn build_white_row(active: &[i8], hi_color: Color) -> Vec<Span<'static>> {
    let mut spans: Vec<Span<'static>> = Vec::new();

    for oct in 0..NUM_OCTAVES {
        for (i, &(idx, label)) in WHITE_KEYS.iter().enumerate() {
            if active.contains(&idx) {
                spans.push(Span::styled(
                    format!(" \u{2605}  "),
                    Style::default()
                        .fg(hi_color)
                        .add_modifier(Modifier::BOLD),
                ));
            } else {
                spans.push(Span::styled(
                    format!(" {}  ", label),
                    Style::default().fg(Color::White),
                ));
            }
        }

        // Octave separator
        if oct < NUM_OCTAVES - 1 {
            spans.push(Span::styled(
                "\u{2502}".to_string(),
                Style::default().fg(Color::DarkGray),
            ));
        }
    }

    spans
}

/// Build a separator line that sits between the black and white key areas.
fn build_separator_row() -> Vec<Span<'static>> {
    let octave_width = WHITE_KEYS.len() * 4; // 28 chars per octave
    let total = octave_width * NUM_OCTAVES + (NUM_OCTAVES - 1); // separators
    vec![Span::styled(
        "\u{2500}".repeat(total),
        Style::default().fg(Color::DarkGray),
    )]
}

/// Build a bottom border row for the white keys.
fn build_bottom_row() -> Vec<Span<'static>> {
    let mut spans: Vec<Span<'static>> = Vec::new();

    for oct in 0..NUM_OCTAVES {
        for _i in 0..WHITE_KEYS.len() {
            spans.push(Span::styled(
                "\u{2584}\u{2584}\u{2584}\u{2584}".to_string(),
                Style::default().fg(Color::DarkGray),
            ));
        }
        if oct < NUM_OCTAVES - 1 {
            spans.push(Span::styled(
                "\u{2534}".to_string(),
                Style::default().fg(Color::DarkGray),
            ));
        }
    }

    spans
}

pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    let active = active_indices(app);
    let hi_color = active_color(app);
    let tone_names = get_tone_names(app);

    let mut lines: Vec<Line<'static>> = Vec::new();

    // Line 0: empty top padding
    lines.push(Line::from(""));

    // Line 1: black key labels
    lines.push(Line::from(build_black_row(&active, hi_color)));

    // Line 2: black key blocks
    lines.push(Line::from(build_black_block_row(&active, hi_color)));

    // Line 3: separator
    lines.push(Line::from(build_separator_row()));

    // Line 4: white key labels
    lines.push(Line::from(build_white_row(&active, hi_color)));

    // Line 5: bottom edge
    lines.push(Line::from(build_bottom_row()));

    // Line 6: empty
    lines.push(Line::from(""));

    // Line 7: tone names below the keyboard
    if !tone_names.is_empty() {
        lines.push(Line::from(vec![
            Span::styled("  Tones: ", Style::default().fg(Color::DarkGray)),
            Span::styled(
                tone_names,
                Style::default()
                    .fg(hi_color)
                    .add_modifier(Modifier::BOLD),
            ),
        ]));
    }

    let block = Block::default()
        .title(" Piano ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::DarkGray));

    let paragraph = Paragraph::new(lines).block(block);
    frame.render_widget(paragraph, area);
}
