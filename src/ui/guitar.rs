use crate::app::App;
use ratatui::{
    layout::Rect,
    style::{Color, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};
use utrp::{
    guitar::{GuitarTarget, Position, Shape},
    theory::chord::Chord,
};

fn note_and_degree(chord: &Chord, position: &Position) -> (String, String) {
    let index = chord
        .tones
        .iter()
        .position(|tone| tone.pc == position.midi % 12)
        .expect("validated chord member");
    (
        chord.tones[index].midi_label(position.midi),
        chord.degree_label(index),
    )
}

fn chord_lines(chord: &Chord, shape: &Shape, region: [u8; 2]) -> Vec<Line<'static>> {
    let mut lines = vec![Line::from(Span::styled(
        format!(
            " {} | inversion {} | frets {}-{}",
            shape.family, shape.inversion, region[0], region[1]
        ),
        Style::default().fg(Color::Cyan),
    ))];
    for string in 1..=6 {
        let position = shape.positions.iter().find(|p| p.string == string);
        let text = position.map_or_else(
            || format!(" {string} | x  (mute)"),
            |p| {
                let (note, degree) = note_and_degree(chord, p);
                let finger = if p.fret == 0 {
                    "open".into()
                } else {
                    p.finger.expect("validated fingering").to_string()
                };
                format!(
                    " {string} | fret {:>2} | {:<5} | {:<3} | finger {finger}",
                    p.fret, note, degree
                )
            },
        );
        let color = if position.is_some_and(|p| p.degree == 1) {
            Color::Green
        } else if position.is_some() {
            Color::Yellow
        } else {
            Color::DarkGray
        };
        lines.push(Line::from(Span::styled(text, Style::default().fg(color))));
    }
    let bass = note_and_degree(chord, &shape.positions[0]).0;
    let top = note_and_degree(chord, shape.positions.last().expect("nonempty")).0;
    let root = shape
        .positions
        .iter()
        .filter(|p| p.degree == 1)
        .map(|p| p.string.to_string())
        .collect::<Vec<_>>()
        .join(",");
    lines.push(Line::from(format!(
        " Bass {bass} | top {top} | root s{root}"
    )));
    lines.push(Line::from(shape.barre.as_ref().map_or(
        " No barre; mute unused strings".into(),
        |b| {
            format!(
                " Barre: fret {} / strings {}-{}",
                b.fret, b.from_string, b.to_string
            )
        },
    )));
    lines.push(Line::from(Span::styled(
        " Fingers 1-4; inversion 0=root, 1=first, ...",
        Style::default().fg(Color::DarkGray),
    )));
    lines
}

fn arpeggio_lines(chord: &Chord, target: &GuitarTarget) -> Vec<Line<'static>> {
    let mut lines = vec![Line::from(Span::styled(
        format!(
            " DETACHED | frets {}-{} | one note at a time",
            target.region[0], target.region[1]
        ),
        Style::default().fg(Color::Cyan),
    ))];
    for (step, position) in target.arpeggio.iter().enumerate() {
        let (note, degree) = note_and_degree(chord, position);
        lines.push(Line::from(Span::styled(
            format!(
                " {}. string {} | fret {:>2} | {note:<5} | {degree}",
                step + 1,
                position.string,
                position.fret
            ),
            Style::default().fg(if position.degree == 1 {
                Color::Green
            } else {
                Color::Yellow
            }),
        )));
    }
    if target.arpeggio.len() != chord.tones.len() {
        lines.push(Line::from(Span::styled(
            " Incomplete path: widen configured region",
            Style::default().fg(Color::Red),
        )));
    }
    lines.push(Line::from(" Follow numbered order; release between notes."));
    lines.push(Line::from(" This is NOT a simultaneous chord grip."));
    lines
}

pub(super) fn lines(app: &App) -> Vec<Line<'static>> {
    let target = &app.session.target().guitar;
    let chord = &app.session.target().music.chord;
    if target.task == "arpeggio_detached" {
        arpeggio_lines(chord, target)
    } else if let Some(shape) = &target.shape {
        chord_lines(chord, shape, target.region)
    } else {
        vec![
            Line::from(Span::styled(
                " No playable chord grip in configured region",
                Style::default().fg(Color::Red),
            )),
            Line::from(" Widen the region/string sets; do not force a grip."),
        ]
    }
}

pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    frame.render_widget(
        Paragraph::new(lines(app)).block(
            Block::default()
                .title(" Guitar | string 1=highest, 6=lowest ")
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::DarkGray)),
        ),
        area,
    );
}
