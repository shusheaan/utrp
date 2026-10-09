"""Render six to eight sourced song cards from TOML into one PNG (rsvg-convert)."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from html import escape
from pathlib import Path
import re
import subprocess
import tomllib
from typing import cast
import unicodedata

if __package__:
    from . import render_key_atlas as atlas
else:
    import render_key_atlas as atlas


@dataclass(frozen=True)
class Style:
    font: str
    tuning: tuple[int, ...]
    keyboard_first: int
    keyboard_last: int
    paper: str
    panel: str
    ink: str
    muted: str
    atlas: atlas.Settings


@dataclass(frozen=True)
class Card:
    title: str
    subtitle: str
    kind: str
    scale: tuple[str, ...]
    notes: tuple[str, ...]
    positions: tuple[str, ...]
    anchor_frets: tuple[int, ...]
    footer: str


@dataclass(frozen=True)
class Song:
    title: str
    info: str
    status: str
    structure: str
    progression: str
    timing: str
    cards: tuple[Card, ...]


def table(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("Expected a TOML table")
    return cast(dict[str, object], value)


def string(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected nonempty text")
    return value


def strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError("Expected an array of strings")
    return tuple(string(item) for item in value)


def integer(value: object, lower: int, upper: int) -> int:
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f"Expected integer in {lower}..{upper}")
    return value


def pitch_class(name: str) -> int:
    match = re.fullmatch(r"([A-G])([#b]?)", name)
    if match is None:
        raise ValueError(f"Invalid pitch class: {name}")
    natural = (0, 2, 4, 5, 7, 9, 11)["CDEFGAB".index(match[1])]
    return (natural + {"": 0, "#": 1, "b": -1}[match[2]]) % 12


def midi_note(name: str) -> int:
    match = re.fullmatch(r"([A-G])([#b]?)(-1|[0-9])", name)
    if match is None:
        raise ValueError(f"Expected a scientific pitch such as F#4: {name}")
    natural = (0, 2, 4, 5, 7, 9, 11)["CDEFGAB".index(match[1])]
    midi = 12 * (int(match[3]) + 1) + natural + {"": 0, "#": 1, "b": -1}[match[2]]
    return integer(midi, 0, 127)


def position_midi(position: str, tuning: tuple[int, ...]) -> int:
    match = re.fullmatch(r"([eBGDAE])(\d{1,2})", position)
    if match is None:
        raise ValueError(f"Invalid string/fret: {position}")
    return tuning["eBGDAE".index(match[1])] + integer(int(match[2]), 0, 24)


def parse_style(raw: dict[str, object], base: atlas.Settings) -> Style:
    guitar = table(raw["guitar"])
    first = integer(guitar["first_fret"], 0, 24)
    last = integer(guitar["last_fret"], first + 1, 24)
    base = replace(base, first_fret=first, last_fret=last)
    theme = base.theme
    return Style(base.text_font, base.tuning, base.first_midi, base.last_midi,
                 theme.paper, theme.panel, theme.ink, theme.muted, base)


def load_style(path: Path) -> Style:
    with path.open("rb") as stream:
        raw = tomllib.load(stream)
    atlas_path = path.parent / string(raw["atlas_config"])
    with atlas_path.open("rb") as stream:
        base = atlas.parse_settings(tomllib.load(stream), atlas_path.parent)
    return parse_style(raw, base)


def visible_anchor(fret: int, first: int, last: int) -> int:
    """Keep a pitch-class landmark visible; never remap actual melody positions."""
    candidates = tuple(value for value in range(first, last + 1) if (value - fret) % 12 == 0)
    if not candidates:
        raise ValueError("Anchor pitch class falls outside the continuous fretboard")
    return min(candidates, key=lambda value: (abs(value - fret), value))


def parse_card(value: object, style: Style) -> Card:
    raw = table(value)
    kind = string(raw["kind"])
    if kind not in ("chord", "melody"):
        raise ValueError("Card kind must be chord or melody")
    scale, notes = strings(raw["scale"]), strings(raw["notes"])
    pcs = tuple(pitch_class(note) for note in scale)
    if len(pcs) != 7 or len(set(pcs)) != 7:
        raise ValueError("Provide a seven-note background collection without duplicates")
    anchors = atlas.six_integers(raw["anchor_frets"], 0, 24)
    first, last = style.atlas.first_fret, style.atlas.last_fret
    for fret in anchors:
        visible_anchor(fret, first, last)
    positions = strings(raw.get("positions", []))
    if kind == "chord":
        chord = tuple(pitch_class(note) for note in notes)
        if not 3 <= len(chord) <= 5 or len(set(chord)) != len(chord) or not set(chord) <= set(pcs):
            raise ValueError("Provide three to five unique chord tones contained in the background")
        intervals = tuple((pc - chord[0]) % 12 for pc in chord)
        accepted = ((0, 4, 7), (0, 3, 7), (0, 3, 6), (0, 2, 7), (0, 5, 7),
                    (0, 4, 7, 11), (0, 3, 7, 10), (0, 4, 7, 10), (0, 3, 6, 10),
                    (0, 4, 7, 9), (0, 3, 7, 9), (0, 5, 7, 10), (0, 4, 7, 2),
                    (0, 3, 7, 2), (0, 4, 7, 11, 2), (0, 3, 7, 10, 2),
                    (0, 4, 7, 10, 2))
        if intervals not in accepted or positions:
            raise ValueError("Unsupported root-ordered triad, seventh or extension")
    else:
        melody = tuple(midi_note(note) for note in notes)
        if not 2 <= len(melody) <= 8 or len(positions) != len(melody):
            raise ValueError("Provide two to eight melody notes and one position per note")
        for midi, position in zip(melody, positions, strict=True):
            if not style.keyboard_first <= midi <= style.keyboard_last:
                raise ValueError("Melody falls outside the keyboard")
            if midi % 12 not in pcs:
                raise ValueError("Melody note missing from background collection")
            if position_midi(position, style.tuning) != midi:
                raise ValueError(f"Guitar position {position} does not match melody MIDI {midi}")
            if not first <= int(position[1:]) <= last:
                raise ValueError("Melody position falls outside the continuous fretboard")
    anchor_pc = pitch_class(notes[0]) if kind == "chord" else midi_note(notes[0]) % 12
    if any((pitch + fret) % 12 != anchor_pc
           for pitch, fret in zip(style.tuning, anchors, strict=True)):
        raise ValueError("Each string anchor must match the chord root / first melody pitch")
    background_key(scale, style)
    return Card(string(raw["title"]), string(raw["subtitle"]), kind, scale, notes,
                positions, anchors, string(raw["footer"]))


def parse_song(raw: dict[str, object], style: Style) -> Song:
    cards = raw["cards"]
    if not isinstance(cards, list) or not 6 <= len(cards) <= 8:
        raise ValueError("Provide six to eight cards")
    headings = tuple(string(raw[key]) for key in
                     ("title", "info", "status", "structure", "progression", "timing"))
    return Song(*headings, tuple(parse_card(card, style) for card in cards))


def text(canvas_width: int, x: float, y: float, value: str, color: str, size: int = 20,
         anchor: str = "start", weight: int = 400) -> str:
    estimated = sum(1.0 if unicodedata.east_asian_width(c) in ("W", "F") else 0.6
                    for c in value) * size
    available = canvas_width - 32 - x
    fit = (f' textLength="{available:g}" lengthAdjust="spacingAndGlyphs"'
           if anchor == "start" and estimated > available else "")
    return (f'<text x="{x:g}" y="{y:g}" fill="{color}" font-size="{size}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{fit}>{escape(value)}</text>')


def rect(x: float, y: float, width: float, height: float, color: str,
         radius: int = 0) -> str:
    return (f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" '
            f'rx="{radius}" fill="{color}"/>')


def circle(x: float, y: float, radius: float, color: str) -> str:
    return f'<circle cx="{x:g}" cy="{y:g}" r="{radius:g}" fill="{color}"/>'


def note_color(pc: int, card: Card, style: Style) -> str:
    """Use the same degree palette as the latest atlas, on every instrument."""
    key = background_key(card.scale, style)
    return style.atlas.colors[key.pitch_classes.index(pc)]


def background_key(scale: tuple[str, ...], style: Style) -> atlas.MajorKey:
    names = set(scale)
    keys = (*style.atlas.overview.keys,
            *(atlas.MajorKey.from_name(name) for name in ("F#", "C#", "Cb")))
    for key in keys:
        spelled = {letter + {-1: "b", 0: "", 1: "#"}[accidental]
                   for letter, accidental in zip(key.letters, key.accidentals, strict=True)}
        if names == spelled:
            return key
    raise ValueError("Background must match a configured major-key collection and spelling")


def atlas_settings(card: Card, style: Style) -> atlas.Settings:
    key = background_key(card.scale, style)
    # Palette and theme come unchanged from the shared atlas configuration.
    # Ring anchors remain the chord root / first melody pitch, not the scale tonic.
    anchors = tuple(visible_anchor(fret, style.atlas.first_fret, style.atlas.last_fret)
                    for fret in card.anchor_frets)
    return replace(style.atlas, key=key, anchor_frets=anchors)


def atlas_tile(card: Card, index: int, style: Style, clefs: tuple[str, str]) -> str:
    settings = atlas_settings(card, style)
    markup = "\n".join(atlas.tile_parts(settings, clefs))
    # Each card reuses the exact atlas tile; namespace its keyboard/staff IDs.
    markup = re.sub(r'\bid="([^"]+)"', lambda match: f'id="card{index}-{match[1]}"', markup)
    return '<g transform="translate(0 100)">' + markup + '</g>'


def melody_staff(card: Card, style: Style, clefs: tuple[str, str]) -> list[str]:
    """Pitched excerpt only: stemless colored notes, no invented rhythmic values."""
    key = background_key(card.scale, style)
    notes = tuple(key.note(midi_note(name)) for name in card.notes)
    if any(note is None for note in notes):
        raise ValueError("Melody pitch is absent from the notated background")
    pitched = tuple(note for note in notes if note is not None)
    low = min(122, *(atlas.staff_y(note, "treble") for note in pitched))
    high = max(178, *(atlas.staff_y(note, "treble") for note in pitched))
    factor = min(1.0, 66 / (high - low))
    bottom = 889 - (high - 178) * factor
    parts = [text(style.atlas.canvas_width, 48, 805, "旋律音高谱 · 实音（不作吉他高八度记谱）· 横向等距只表先后，不表时值", style.muted, 18)]
    for index in range(5):
        parts.append(atlas.line(64, bottom - index * 14 * factor, style.atlas.canvas_width - 60, bottom - index * 14 * factor,
                                style.ink, 1))
    scale = 14 * factor / 194
    parts.append(f'<path data-melody-clef="treble" d="{clefs[0]}" fill="{style.ink}" '
                 f'transform="translate(72 {bottom - 14 * factor + 170 * scale:g}) '
                 f'scale({scale:g} {-scale:g})"/>')
    parts.append(f'<g transform="translate(110 {bottom:g}) scale({factor:g}) translate(-1078 -178)">')
    parts.extend(atlas.key_signature_svg(key, "treble", style.ink))
    parts.append('</g>')
    for index, (name, position, note) in enumerate(zip(card.notes, card.positions, pitched, strict=True)):
        x = 280 + index * (style.atlas.canvas_width - 420) / (len(card.notes) - 1)
        raw_y = atlas.staff_y(note, "treble")
        y = bottom + (raw_y - 178) * factor
        parts.append(f'<g data-melody-index="{index}" data-midi="{note.midi}">')
        parts.extend(atlas.line(x - 16, bottom + (ledger - 178) * factor,
                                x + 16, bottom + (ledger - 178) * factor, style.ink, 1)
                     for ledger in atlas.ledger_lines(raw_y, 178, 14))
        parts.extend([circle(x, y, 11, note_color(note.midi % 12, card, style)),
                      atlas.pitch_label(x, y + 4, note.letter, note.accidental, 13),
                      text(style.atlas.canvas_width, x, 921, f"{index + 1} · {name}", style.ink, 17, "middle"),
                      text(style.atlas.canvas_width, x, 946, position, style.muted, 17, "middle"), '</g>'])
    return parts


def render_card(card: Card, index: int, style: Style, clefs: tuple[str, str]) -> str:
    settings = atlas_settings(card, style)
    reference = card.notes[0] if card.kind == "chord" else card.notes[0][:-1]
    parts = [f'<g id="card-{index}" transform="translate(0 {410 + (index - 1) * 1030})">',
             rect(0, 0, style.atlas.canvas_width, 1010, style.panel),
             text(style.atlas.canvas_width, 32, 39, f"{index:02d}  {card.title}", style.ink, 26, weight=700),
             text(style.atlas.canvas_width, 32, 73, card.subtitle, style.muted, 19),
             atlas_tile(card, index, style, clefs)]
    if card.kind == "melody":
        parts.extend(melody_staff(card, style, clefs))
    else:
        parts.append(text(style.atlas.canvas_width, 48, 829, "和弦音  " + "  ·  ".join(card.notes), style.ink, 24))
        parts.append(text(style.atlas.canvas_width, 48, 869, "背景音集  " + "  ".join(card.scale) +
                          f"  /  五线谱用 {settings.key.name} major 调号（本格音集，不是全曲定调）",
                          style.muted, 20))
        parts.append(text(style.atlas.canvas_width, 48, 916, f"六弦分别圈出 {reference}；连续 {settings.first_fret}–{settings.last_fret} 品音位地图，不是同时按下的 voicing。",
                          style.muted, 20))
    parts.extend([text(style.atlas.canvas_width, 32, 992, card.footer, style.muted, 18), '</g>'])
    return "\n".join(parts)


def render_svg(song: Song, style: Style, clefs: tuple[str, str]) -> str:
    height = 420 + len(song.cards) * 1030
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{style.atlas.canvas_width}" height="{height}" '
             f'viewBox="0 0 {style.atlas.canvas_width} {height}" role="img">',
             f'<title>{escape(song.title)}</title>',
             f'<desc>{escape(song.status + "；" + song.progression)}</desc>',
             rect(0, 0, style.atlas.canvas_width, height, style.paper),
             f'<g font-family="{escape(style.font, quote=True)}">',
             text(style.atlas.canvas_width, 48, 42, "UTRP / COVER STUDY / PIANO + GUITAR", style.muted, 17),
             text(style.atlas.canvas_width, 48, 104, song.title, style.ink, 43, weight=700),
             text(style.atlas.canvas_width, 48, 145, song.info, style.muted, 23),
             text(style.atlas.canvas_width, 48, 183, song.status, style.atlas.colors[0], 21),
             text(style.atlas.canvas_width, 48, 227, song.structure, style.ink, 21),
             text(style.atlas.canvas_width, 48, 273, song.progression, style.ink, 28, weight=600),
             text(style.atlas.canvas_width, 48, 313, song.timing, style.muted, 20),
             text(style.atlas.canvas_width, 48, 350, "配色沿用 atlas：本格音集 1 红、2/3 绿、4/5 鲑鱼色、6/7 蓝；圆环＝根音 / 旋律首音。", style.muted, 19),
             text(style.atlas.canvas_width, 48, 382, "每格：上排高低音五线谱 + 键盘，下排等宽连续吉他指板；下方 12 品为横向双点。", style.muted, 19)]
    parts.extend(render_card(card, index, style, clefs) for index, card in enumerate(song.cards, 1))
    parts.extend(['</g>', '</svg>'])
    return "\n".join(parts) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song", type=Path)
    parser.add_argument("--style", type=Path,
                        default=Path(__file__).resolve().parents[1] / "config/cover-atlas.toml")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    output = args.song.with_suffix(".png")
    try:
        if output.exists() and not args.force:
            raise ValueError(f"Already exists: {output}; use --force to regenerate")
        style = load_style(args.style)
        clefs = atlas.load_clefs(style.atlas.music_font)
        with args.song.open("rb") as stream:
            song = parse_song(tomllib.load(stream), style)
        result = subprocess.run(["rsvg-convert", "--format=png"],
                                input=render_svg(song, style, clefs).encode(), capture_output=True,
                                check=True)
        output.write_bytes(result.stdout)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(output)


if __name__ == "__main__":
    main()
