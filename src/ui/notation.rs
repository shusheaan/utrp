use crate::app::App;
use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};
use utrp::theory::tone::Tone;

pub const MIN_WIDTH: u16 = 48;
const BASS_BOTTOM: i16 = 18; // G2, with C0 = 0 diatonic steps.
const TREBLE_TOP: i16 = 38; // F5.
const MIDDLE_C: i16 = 28;
const LABEL_WIDTH: usize = 5;
const HEADER_ROWS: u16 = 3;

#[derive(Debug, Clone, PartialEq, Eq)]
struct WrittenNote {
    step: i16,
    marker: String,
    root: bool,
}

fn written_note(midi: u8, tone: &Tone, root: bool) -> Result<WrittenNote, String> {
    let letter = tone.name.chars().next().ok_or("empty note spelling")?;
    let index = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
        .iter()
        .position(|c| *c == letter)
        .ok_or("invalid note letter")?;
    let accidental = &tone.name[1..];
    let mut offset = 0_i16;
    for c in accidental.chars() {
        offset += match c {
            '#' => 1,
            'b' => -1,
            _ => return Err("invalid note accidental".into()),
        };
    }
    let natural = [0, 2, 4, 5, 7, 9, 11][index];
    let unaltered = i16::from(midi) - offset;
    if (unaltered - natural).rem_euclid(12) != 0 || midi % 12 != tone.pc {
        return Err("note spelling does not match actual pitch".into());
    }
    // Subtract the written accidental before finding the octave: B#3=C4,
    // Cb4=B3. MIDI octave alone is not the written octave at this boundary.
    let octave = (unaltered - natural).div_euclid(12) - 1;
    Ok(WrittenNote {
        step: octave * 7 + index as i16,
        marker: format!(
            "{}●{letter}{octave}",
            if accidental.is_empty() {
                "♮".to_owned()
            } else {
                accidental.replace('#', "♯").replace('b', "♭")
            }
        ),
        root,
    })
}

fn target_notes(app: &App) -> Result<Vec<WrittenNote>, String> {
    let target = app.session.target();
    let pitches: Vec<u8> = if app.instrument == "piano" {
        target.piano_notes.clone()
    } else if target.guitar.task == "arpeggio_detached" {
        if target.guitar.arpeggio.len() != target.music.chord.tones.len() {
            return Err("incomplete arpeggio path".into());
        }
        target.guitar.arpeggio.iter().map(|p| p.midi).collect()
    } else {
        target
            .guitar
            .shape
            .as_ref()
            .map_or_else(Vec::new, |s| s.positions.iter().map(|p| p.midi).collect())
    };
    pitches
        .into_iter()
        .map(|midi| {
            let tone = target
                .music
                .chord
                .tones
                .iter()
                .find(|t| t.pc == midi % 12)
                .ok_or("actual note is not a chord member")?;
            written_note(midi, tone, tone.pc == target.music.chord.root.pc)
        })
        .collect()
}

fn bounds(notes: &[WrittenNote]) -> (i16, i16) {
    notes.iter().fold((BASS_BOTTOM, TREBLE_TOP), |(lo, hi), n| {
        (lo.min(n.step), hi.max(n.step))
    })
}

pub fn required_height(app: &App) -> u16 {
    let notes = target_notes(app).unwrap_or_default();
    let (low, high) = bounds(&notes);
    (high - low + 1) as u16 + HEADER_ROWS + 2
}

pub(super) fn panel_width(app: &App) -> u16 {
    required_width(&target_notes(app).unwrap_or_default())
}

/// Narrow screens use successive staff systems, never drop note columns.
pub(super) fn compact_lines(app: &App, width: u16) -> Vec<Line<'static>> {
    let mut rows = vec![
        Line::from("Staff | concert pitch"),
        Line::from("Treble upper / Bass lower; no key signature"),
        Line::from("● note; ♮/♯/♭ per note"),
    ];
    let notes = match target_notes(app) {
        Ok(notes) if !notes.is_empty() => notes,
        Ok(_) => {
            rows.push(Line::from("No notes: no playable target"));
            return rows;
        }
        Err(reason) => {
            rows.push(Line::from(format!("No notes: {reason}")));
            return rows;
        }
    };
    let column = column_width(&notes);
    let per_system = (usize::from(width).saturating_sub(LABEL_WIDTH) / column).max(1);
    let detached =
        app.instrument == "guitar" && app.session.target().guitar.task == "arpeggio_detached";
    rows.push(Line::from(if detached {
        "Arpeggio L->R; continue on next staff"
    } else {
        "Simultaneous (all staff groups together)"
    }));
    for (group, notes) in notes.chunks(per_system).enumerate() {
        let column = column_width(notes);
        rows.push(Line::from(format!(
            "{}{}",
            " ".repeat(LABEL_WIDTH),
            (0..notes.len())
                .map(|i| format!("{:^column$}", format!("[{}]", group * per_system + i + 1)))
                .collect::<String>()
        )));
        rows.extend(staff_rows(notes, usize::from(width)));
    }
    rows
}

fn column_width(notes: &[WrittenNote]) -> usize {
    notes
        .iter()
        .map(|n| n.marker.chars().count() + 4)
        .max()
        .unwrap_or(8)
}

fn required_width(notes: &[WrittenNote]) -> u16 {
    MIN_WIDTH.max((LABEL_WIDTH + notes.len() * column_width(notes) + 2) as u16)
}

fn staff_line(step: i16) -> bool {
    matches!(step, 18 | 20 | 22 | 24 | 26 | 30 | 32 | 34 | 36 | 38)
}

fn ledger_line(step: i16, note: &WrittenNote) -> bool {
    step.rem_euclid(2) == 0
        && ((step < BASS_BOTTOM && note.step <= step)
            || (step > TREBLE_TOP && note.step >= step)
            || (step == MIDDLE_C && note.step == MIDDLE_C))
}

fn note_column(step: i16, note: &WrittenNote, width: usize) -> Vec<Span<'static>> {
    let mut background = vec![if staff_line(step) { b'-' } else { b' ' }; width];
    // These BMP notation symbols each occupy one terminal column.
    let marker_width = note.marker.chars().count();
    let left = (width - marker_width) / 2;
    if ledger_line(step, note) {
        background[left - 1..=left + marker_width].fill(b'-');
    }
    let line_style = Style::default().fg(Color::DarkGray);
    if note.step != step {
        return vec![Span::styled(
            String::from_utf8(background).expect("ASCII staff"),
            line_style,
        )];
    }
    vec![
        Span::styled(
            String::from_utf8(background[..left].to_vec()).expect("ASCII staff"),
            line_style,
        ),
        Span::styled(
            note.marker.clone(),
            Style::default()
                .fg(if note.root {
                    Color::Green
                } else {
                    Color::Yellow
                })
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(
            String::from_utf8(background[left + marker_width..].to_vec()).expect("ASCII staff"),
            line_style,
        ),
    ]
}

fn staff_rows(notes: &[WrittenNote], width: usize) -> Vec<Line<'static>> {
    let (low, high) = bounds(notes);
    let column = column_width(notes);
    (low..=high)
        .rev()
        .map(|step| {
            let letter = ['C', 'D', 'E', 'F', 'G', 'A', 'B'][step.rem_euclid(7) as usize];
            let label = format!("{letter}{}", step.div_euclid(7));
            let mut spans = vec![Span::styled(
                format!("{label:>3} |"),
                Style::default().fg(Color::DarkGray),
            )];
            for note in notes {
                spans.extend(note_column(step, note, column));
            }
            let remaining = width.saturating_sub(LABEL_WIDTH + notes.len() * column);
            spans.push(Span::styled(
                if staff_line(step) { "-" } else { " " }.repeat(remaining),
                Style::default().fg(Color::DarkGray),
            ));
            Line::from(spans)
        })
        .collect()
}

pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    let block = Block::default()
        .title(" Staff | concert pitch ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::DarkGray));
    let notes = match target_notes(app) {
        Ok(notes) => notes,
        Err(reason) => {
            frame.render_widget(
                Paragraph::new(format!("No notes: {reason}")).block(block),
                area,
            );
            return;
        }
    };
    let height = required_height(app);
    let width = required_width(&notes);
    if area.width < width || area.height < height {
        frame.render_widget(
            Paragraph::new(format!("Resize staff to at least {width}x{height}")).block(block),
            area,
        );
        return;
    }
    if notes.is_empty() {
        frame.render_widget(
            Paragraph::new("No notes: no playable target").block(block),
            area,
        );
        return;
    }
    let task =
        if app.instrument == "guitar" && app.session.target().guitar.task == "arpeggio_detached" {
            "Arpeggio L->R"
        } else {
            "Simultaneous"
        };
    let mut rows = vec![
        Line::styled(
            "Treble upper / Bass lower; no key signature",
            Style::default().fg(Color::Cyan),
        ),
        Line::styled(
            format!("{task} | ● note; ♮/♯/♭ per note"),
            Style::default().fg(Color::DarkGray),
        ),
        Line::styled(
            format!(
                "{}{}",
                " ".repeat(LABEL_WIDTH),
                (1..=notes.len())
                    .map(|i| format!("{:^width$}", format!("[{i}]"), width = column_width(&notes)))
                    .collect::<String>()
            ),
            Style::default().fg(Color::DarkGray),
        ),
    ];
    rows.extend(staff_rows(&notes, usize::from(block.inner(area).width)));
    frame.render_widget(Paragraph::new(rows).block(block), area);
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::{backend::TestBackend, Terminal};
    use utrp::{
        config::{Config, Templates},
        guitar::{Position, Shape},
        session::Session,
        simulator,
        theory::chord::Chord,
    };

    fn app(instrument: &str, notes: &[(u8, &str)]) -> App {
        let config = Config::load(None).unwrap();
        let mut session = Session::new(
            simulator::stream(&config, Templates::load(None).unwrap(), 42, 48).unwrap(),
            config.session,
            0,
        );
        let target = &mut session.history[0];
        target.music.chord = Chord::from_tones(
            notes
                .iter()
                .map(|(_, name)| Tone::parse(name).unwrap())
                .collect(),
            vec![1; notes.len()],
        );
        target.piano_notes = notes.iter().map(|(midi, _)| *midi).collect();
        let positions: Vec<_> = notes
            .iter()
            .enumerate()
            .map(|(i, (midi, _))| Position {
                string: (6 - i) as u8,
                fret: 0,
                midi: *midi,
                degree: 1,
                finger: Some(0),
            })
            .collect();
        target.guitar.task = "chord".into();
        target.guitar.arpeggio = positions.clone();
        target.guitar.shape = Some(Shape {
            positions,
            muted: vec![],
            barre: None,
            inversion: 0,
            family: "test".into(),
        });
        App::new(session, instrument.into(), None, None)
    }

    fn rendered(app: &App, width: u16, height: u16) -> Vec<String> {
        let mut terminal = Terminal::new(TestBackend::new(width, height)).unwrap();
        terminal
            .draw(|frame| render(frame, app, frame.area()))
            .unwrap();
        terminal
            .backend()
            .buffer()
            .content
            .chunks(usize::from(width))
            .map(|cells| cells.iter().map(|c| c.symbol()).collect())
            .collect()
    }

    #[test]
    fn actual_e2_c4_d6_are_not_pitch_class_folded() {
        let app = app("guitar", &[(40, "E"), (60, "C"), (86, "D")]);
        let notes = target_notes(&app).unwrap();
        assert_eq!(
            notes.iter().map(|n| n.step).collect::<Vec<_>>(),
            [16, 28, 43]
        );
        assert_eq!(required_height(&app), 33);
        let rows = rendered(&app, MIN_WIDTH, required_height(&app));
        let origin = 1 + HEADER_ROWS as usize;
        for note in notes {
            let row = origin + (43 - note.step) as usize;
            assert!(rows[row].contains(&note.marker), "missing {}", note.marker);
        }
        let text = rows.join("\n");
        for label in [
            "concert pitch",
            "Treble upper",
            "Bass lower",
            "Simultaneous",
        ] {
            assert!(text.contains(label));
        }
    }

    #[test]
    fn piano_uses_actual_notes_including_distinct_octaves() {
        let app = app("piano", &[(48, "C"), (60, "C"), (72, "C"), (84, "C")]);
        let notes = target_notes(&app).unwrap();
        assert_eq!(
            notes.iter().map(|n| n.step).collect::<Vec<_>>(),
            [21, 28, 35, 42]
        );
        let text = rendered(&app, MIN_WIDTH, required_height(&app)).join("\n");
        for marker in ["♮●C3", "♮●C4", "♮●C5", "♮●C6"] {
            assert_eq!(text.matches(marker).count(), 1);
        }
    }

    #[test]
    fn all_138_standard_guitar_positions_retain_written_pitch_and_octave() {
        let names = [
            "C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B",
        ];
        let letter_indices = [0, 0, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6];
        let mut checked = 0;
        for open in [40_u8, 45, 50, 55, 59, 64] {
            for fret in 0..=22 {
                let midi = open + fret;
                let pc = usize::from(midi % 12);
                let octave = i16::from(midi / 12) - 1;
                let note = written_note(midi, &Tone::parse(names[pc]).unwrap(), false).unwrap();
                assert_eq!(note.step, octave * 7 + letter_indices[pc]);
                assert!(note
                    .marker
                    .ends_with(&format!("{}{octave}", &names[pc][..1])));
                let (low, high) = bounds(std::slice::from_ref(&note));
                let rows = staff_rows(std::slice::from_ref(&note), usize::from(MIN_WIDTH - 2));
                assert_eq!(rows.len(), (high - low + 1) as usize);
                let text: String = rows[(high - note.step) as usize]
                    .spans
                    .iter()
                    .map(|s| s.content.as_ref())
                    .collect();
                assert!(text.contains(&note.marker));
                checked += 1;
            }
        }
        assert_eq!(checked, 138);
    }

    #[test]
    fn extreme_midi_0_and_127_extend_the_staff_without_folding() {
        let app = app("piano", &[(0, "C"), (127, "G")]);
        let notes = target_notes(&app).unwrap();
        assert_eq!(notes.iter().map(|n| n.step).collect::<Vec<_>>(), [-7, 67]);
        assert_eq!(required_height(&app), 80);
        let rows = rendered(&app, MIN_WIDTH, required_height(&app));
        let top = 1 + HEADER_ROWS as usize;
        assert!(rows[top].contains("♮●G9"));
        assert!(rows[rows.len() - 2].contains("♮●C-1"));
        assert_eq!(rows.join("\n").matches('●').count(), 3); // Two notes + legend.
    }

    #[test]
    fn unicode_note_markers_use_terminal_columns_not_utf8_bytes() {
        for (midi, name) in [(60, "C"), (61, "C#"), (59, "Cb"), (61, "B##"), (58, "Cbb")] {
            let note = written_note(midi, &Tone::parse(name).unwrap(), false).unwrap();
            let width = column_width(std::slice::from_ref(&note));
            let spans = note_column(note.step, &note, width);
            assert_eq!(Line::from(spans).width(), width);
            assert!(note.marker.len() > note.marker.chars().count());
        }
    }

    #[test]
    fn accidentals_determine_written_octave_including_double_accidentals() {
        for (midi, name, step, marker) in [
            (60, "B#", 27, "♯●B3"),
            (59, "Cb", 28, "♭●C4"),
            (61, "B##", 27, "♯♯●B3"),
            (58, "Cbb", 28, "♭♭●C4"),
            (66, "F#", 31, "♯●F4"),
            (70, "Bb", 34, "♭●B4"),
            (60, "C", 28, "♮●C4"),
        ] {
            let note = written_note(midi, &Tone::parse(name).unwrap(), false).unwrap();
            assert_eq!((note.step, note.marker.as_str()), (step, marker));
        }
        assert!(written_note(61, &Tone::parse("C").unwrap(), false).is_err());
    }

    #[test]
    fn grand_staff_and_local_ledgers_have_exact_diatonic_positions() {
        for step in 16..=44 {
            assert_eq!(
                staff_line(step),
                [18, 20, 22, 24, 26, 30, 32, 34, 36, 38].contains(&step)
            );
        }
        let low = written_note(40, &Tone::parse("E").unwrap(), false).unwrap();
        let middle = written_note(60, &Tone::parse("C").unwrap(), false).unwrap();
        let high = written_note(86, &Tone::parse("D").unwrap(), false).unwrap();
        assert!(ledger_line(16, &low));
        assert!(ledger_line(28, &middle));
        assert!(ledger_line(40, &high));
        assert!(ledger_line(42, &high));
        assert!(!ledger_line(28, &low));
        assert!(!ledger_line(41, &high));
        let center: String = note_column(28, &middle, 8)
            .iter()
            .map(|s| s.content.as_ref())
            .collect();
        assert!(center.contains("-♮●C4-"));
    }

    #[test]
    fn detached_path_order_is_preserved_in_independent_columns() {
        let mut app = app("guitar", &[(60, "C"), (64, "E"), (67, "G")]);
        let guitar = &mut app.session.history[0].guitar;
        guitar.task = "arpeggio_detached".into();
        guitar.arpeggio.reverse();
        let notes = target_notes(&app).unwrap();
        assert_eq!(
            notes.iter().map(|n| n.marker.as_str()).collect::<Vec<_>>(),
            ["♮●G4", "♮●E4", "♮●C4"]
        );
        let rows = rendered(&app, MIN_WIDTH, required_height(&app));
        let positions: Vec<_> = notes
            .iter()
            .map(|n| rows.iter().find_map(|r| r.find(&n.marker)).unwrap())
            .collect();
        assert!(positions.windows(2).all(|p| p[0] < p[1]));
        let text = rows.join("\n");
        assert!(text.contains("Arpeggio L->R"));
        for label in ["[1]", "[2]", "[3]"] {
            assert!(text.contains(label));
        }
    }

    #[test]
    fn adjacent_notes_and_accidentals_never_overwrite_or_clip() {
        let app = app("piano", &[(60, "B#"), (59, "Cb"), (61, "C#"), (62, "D")]);
        let notes = target_notes(&app).unwrap();
        let text = rendered(&app, required_width(&notes), required_height(&app)).join("\n");
        for note in notes {
            assert_eq!(text.matches(&note.marker).count(), 1);
        }
        let double = app_for_double_accidentals();
        let notes = target_notes(&double).unwrap();
        let text = rendered(&double, required_width(&notes), required_height(&double)).join("\n");
        for note in notes {
            assert_eq!(text.matches(&note.marker).count(), 1);
        }
    }

    fn app_for_double_accidentals() -> App {
        app(
            "piano",
            &[(61, "B##"), (58, "Cbb"), (67, "F##"), (69, "Bbb")],
        )
    }

    #[test]
    fn mobile_staff_groups_preserve_every_pitch_and_note_number() {
        let app = app("piano", &[(40, "E"), (58, "Cbb"), (61, "B##"), (86, "D")]);
        for width in [20, 28, 32, 40, 48, 72] {
            let rows = compact_lines(&app, width);
            // Explanatory text wraps separately; notation rows must fit intact.
            for row in rows.iter().skip(4) {
                assert!(row.width() <= usize::from(width), "{width}: {row:?}");
            }
            let text = rows
                .iter()
                .map(ToString::to_string)
                .collect::<Vec<_>>()
                .join("\n");
            for note in target_notes(&app).unwrap() {
                assert_eq!(text.matches(&note.marker).count(), 1, "{width}: {text}");
            }
            for i in 1..=4 {
                assert_eq!(text.matches(&format!("[{i}]")).count(), 1);
            }
            assert!(text.contains("Simultaneous"));
        }
    }

    #[test]
    fn small_area_warns_instead_of_silently_cropping_notes() {
        let app = app("guitar", &[(40, "E"), (60, "C"), (86, "D")]);
        for (width, height) in [
            (MIN_WIDTH, required_height(&app) - 1),
            (MIN_WIDTH - 1, required_height(&app)),
        ] {
            let text = rendered(&app, width, height).join("\n");
            assert!(text.contains("Resize staff"));
            for marker in ["♮●E2", "♮●C4", "♮●D6"] {
                assert!(!text.contains(marker));
            }
        }
    }

    #[test]
    fn unavailable_or_incomplete_targets_report_no_notes() {
        let mut app = app("guitar", &[(60, "C"), (64, "E"), (67, "G")]);
        app.session.history[0].guitar.shape = None;
        assert!(rendered(&app, MIN_WIDTH, required_height(&app))
            .join("\n")
            .contains("No notes"));
        app.session.history[0].guitar.task = "arpeggio_detached".into();
        app.session.history[0].guitar.arpeggio.pop();
        assert!(rendered(&app, MIN_WIDTH, required_height(&app))
            .join("\n")
            .contains("No notes: incomplete"));
    }
}
