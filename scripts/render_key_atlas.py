"""Generate single-key or 12-major-key keyboard, staff and guitar SVG atlases.

Requires Python >= 3.11 and fontTools. Musical clefs are embedded as paths;
the generated SVG needs no music font, JavaScript, or network access.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from html import escape
from pathlib import Path
import re
import tomllib
from typing import cast

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont


@dataclass(frozen=True)
class Theme:
    paper: str
    panel: str
    ink: str
    muted: str
    line: str
    black_key: str


@dataclass(frozen=True)
class Blocks:
    upper_string: int
    first_fret: int


@dataclass(frozen=True)
class SpelledNote:
    midi: int
    letter: str
    accidental: int
    octave: int
    degree: int

    def name(self) -> str:
        sign = {-1: "♭", 0: "", 1: "♯"}[self.accidental]
        return f"{self.letter}{sign}{self.octave}"

    def staff_step(self) -> int:
        return self.octave * 7 + "CDEFGAB".index(self.letter)


@dataclass(frozen=True)
class MajorKey:
    name: str
    pitch_classes: tuple[int, ...]
    letters: tuple[str, ...]
    accidentals: tuple[int, ...]

    @classmethod
    def from_name(cls, name: str) -> MajorKey:
        if re.fullmatch(r"[A-G][b#]?", name) is None:
            raise ValueError("Key must be an uppercase tonic with optional b or #")
        letters, naturals = "CDEFGAB", (0, 2, 4, 5, 7, 9, 11)
        start = letters.index(name[0])
        tonic = naturals[start] + {"": 0, "b": -1, "#": 1}[name[1:]]
        pcs = tuple((tonic + step) % 12 for step in (0, 2, 4, 5, 7, 9, 11))
        names = tuple(letters[(start + index) % 7] for index in range(7))
        accidentals = tuple((pc - naturals[letters.index(letter)] + 6) % 12 - 6
                            for pc, letter in zip(pcs, names))
        if any(abs(accidental) > 1 for accidental in accidentals):
            raise ValueError("Use a major-key spelling without double accidentals")
        return cls(name, pcs, names, accidentals)

    def note(self, midi: int) -> SpelledNote | None:
        if type(midi) is not int or not 0 <= midi <= 127:
            raise ValueError("MIDI pitch must be an integer in 0–127")
        if midi % 12 not in self.pitch_classes:
            return None
        degree = self.pitch_classes.index(midi % 12)
        letter, accidental = self.letters[degree], self.accidentals[degree]
        natural = (0, 2, 4, 5, 7, 9, 11)["CDEFGAB".index(letter)]
        octave = (midi - natural - accidental) // 12 - 1
        return SpelledNote(midi, letter, accidental, octave, degree)

    def notes(self, first: int, last: int) -> tuple[SpelledNote, ...]:
        return tuple(note for midi in range(first, last + 1)
                     if (note := self.note(midi)) is not None)


@dataclass(frozen=True)
class Overview:
    keys: tuple[MajorKey, ...]
    columns: int
    rows: int
    gap: int


@dataclass(frozen=True)
class Settings:
    title: str
    colors: tuple[str, ...]
    music_font: Path
    text_font: str
    theme: Theme
    tuning: tuple[int, ...]
    anchor_frets: tuple[int, ...]
    frets_before_anchor: int
    frets_after_anchor: int
    first_midi: int
    last_midi: int
    blocks: Blocks
    key: MajorKey
    overview: Overview


@dataclass(frozen=True)
class Note:
    midi: int
    letter: str
    sharp: bool
    octave: int
    degree: int

    @classmethod
    def from_midi(cls, midi: int) -> Note:
        if type(midi) is not int or not 0 <= midi <= 127:
            raise ValueError("MIDI pitch must be an integer in 0–127")
        degree = (0, 0, 1, 1, 2, 3, 3, 4, 4, 5, 5, 6)[midi % 12]
        return cls(midi, "CDEFGAB"[degree], midi % 12 in (1, 3, 6, 8, 10),
                   midi // 12 - 1, degree)

    def name(self) -> str:
        return f'{self.letter}{"♯" if self.sharp else ""}{self.octave}'

    def staff_step(self) -> int:
        return self.octave * 7 + self.degree


def nonempty_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected nonempty text")
    return value


def color(value: object) -> str:
    result = nonempty_text(value)
    if re.fullmatch(r"#[0-9a-fA-F]{6}", result) is None:
        raise ValueError("Colors must use #RRGGBB")
    return result


def parse_settings(raw: dict[str, object], base: Path) -> Settings:
    key = MajorKey.from_name(nonempty_text(raw["key"]))
    palette = raw["colors"]
    if not isinstance(palette, list) or len(palette) != 7:
        raise ValueError("Provide exactly 7 scale-degree colors")
    colors = tuple(color(item) for item in palette)
    theme = raw["theme"]
    if not isinstance(theme, dict):
        raise ValueError("Expected a theme table")
    table = cast(dict[str, object], theme)
    font = Path(nonempty_text(raw["music_font"]))
    tuning = six_integers(raw["tuning"], 0, 103)
    anchors = six_integers(raw["anchor_frets"], 0, 21)
    before = bounded_integer(raw["frets_before_anchor"], 0, 5)
    after = bounded_integer(raw["frets_after_anchor"], 0, 5)
    if not 4 <= before + after + 1 <= 8:
        raise ValueError("Show 4–8 fret columns per guitar panel")
    if any((pitch + fret) % 12 != key.pitch_classes[0] for pitch, fret in zip(tuning, anchors)):
        raise ValueError("Every guitar anchor must match the key tonic")
    if any(fret - before < 0 or fret + after > 24 for fret in anchors):
        raise ValueError("A guitar window falls outside frets 0–24")
    first = bounded_integer(raw["first_midi"], 36, 59)
    last = bounded_integer(raw["last_midi"], 60, 84)
    if Note.from_midi(first).sharp or Note.from_midi(last).sharp:
        raise ValueError("Keyboard endpoints must be white keys")
    return Settings(nonempty_text(raw["title"]),
                    colors, font if font.is_absolute() else base / font,
                    nonempty_text(raw["text_font"]),
                    Theme(*(color(table[key]) for key in
                            ("paper", "panel", "ink", "muted", "line", "black_key"))),
                    tuning, anchors, before, after, first, last,
                    parse_blocks(raw["blocks"], tuning, key), key,
                    parse_overview(raw["overview"]))


def parse_overview(value: object) -> Overview:
    if not isinstance(value, dict):
        raise ValueError("Expected an overview table")
    raw = cast(dict[str, object], value)
    keys_raw = raw["keys"]
    if not isinstance(keys_raw, list) or len(keys_raw) != 12:
        raise ValueError("Overview requires 12 major keys")
    keys = tuple(MajorKey.from_name(nonempty_text(key)) for key in keys_raw)
    if len({key.pitch_classes[0] for key in keys}) != 12:
        raise ValueError("Overview must cover each tonic pitch class exactly once")
    columns = bounded_integer(raw["columns"], 1, 12)
    rows = bounded_integer(raw["rows"], 1, 12)
    if columns * rows != 12:
        raise ValueError("Overview grid must contain exactly 12 cells")
    return Overview(keys, columns, rows, bounded_integer(raw["gap"], 0, 100))


def parse_blocks(value: object, tuning: tuple[int, ...], key: MajorKey) -> Blocks:
    if not isinstance(value, dict):
        raise ValueError("Expected a blocks table")
    raw = cast(dict[str, object], value)
    upper = bounded_integer(raw["upper_string"], 1, 5) - 1
    first = bounded_integer(raw["first_fret"], 0, 19)
    if tuning[upper] - tuning[upper + 1] != 5:
        raise ValueError("Aligned blocks require two strings tuned a perfect fourth apart")
    if (tuning[upper] + first) % 12 != key.pitch_classes[1]:
        raise ValueError("The upper-left block note must be scale degree 2")
    return Blocks(upper, first)


def transpose_settings(settings: Settings, key: MajorKey) -> Settings:
    delta = (key.pitch_classes[0] - settings.key.pitch_classes[0]) % 12
    def fret_near(reference: int, lower: int, upper: int) -> int:
        candidates = tuple(fret for fret in range(lower, upper + 1)
                           if (fret - reference - delta) % 12 == 0)
        if not candidates:
            raise ValueError("No transposed anchor fits the configured fret window")
        return min(candidates, key=lambda fret: (abs(fret - reference), fret))
    anchors = tuple(fret_near(fret, settings.frets_before_anchor,
                             24 - settings.frets_after_anchor) for fret in settings.anchor_frets)
    block = replace(settings.blocks, first_fret=fret_near(settings.blocks.first_fret, 0, 19))
    return replace(settings, key=key, title=f"{key.name} major", anchor_frets=anchors, blocks=block)


def bounded_integer(value: object, lower: int, upper: int) -> int:
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f"Expected an integer in {lower}–{upper}")
    return value


def six_integers(value: object, lower: int, upper: int) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != 6:
        raise ValueError("Provide six string values, high e to low E")
    return tuple(bounded_integer(item, lower, upper) for item in value)


def scale_notes(first: int, last: int) -> tuple[Note, ...]:
    return tuple(note for midi in range(first, last + 1)
                 if not (note := Note.from_midi(midi)).sharp)


def load_clefs(path: Path) -> tuple[str, str]:
    """Read the two actual font glyphs; do not depend on viewer font fallback."""
    with TTFont(path) as font:
        cmap = font.getBestCmap()
        if cmap is None or any(code not in cmap for code in (0x1D11E, 0x1D122)):
            raise ValueError("music_font must contain both G-clef and F-clef glyphs")
        # Placement is calibrated to FreeSerif's glyph metrics, not arbitrary fonts.
        family = font["name"].getDebugName(1)
        if family != "FreeSerif":
            raise ValueError("Use FreeSerif for the calibrated clef placement")
        glyphs = font.getGlyphSet()
        paths: list[str] = []
        for code in (0x1D11E, 0x1D122):
            pen = SVGPathPen(glyphs)
            glyphs[cmap[code]].draw(pen)
            paths.append(pen.getCommands())
    return paths[0], paths[1]


def text(x: float, y: float, value: str, size: int, fill: str,
         anchor: str = "start", weight: int = 400) -> str:
    return (f'<text x="{x:g}" y="{y:g}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{escape(value)}</text>')


def rect(x: float, y: float, width: float, height: float, fill: str,
         radius: int = 0, extra: str = "") -> str:
    return (f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" '
            f'rx="{radius}" fill="{fill}" {extra}/>')


def line(x1: float, y1: float, x2: float, y2: float, stroke: str,
         width: float = 1) -> str:
    return (f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" '
            f'stroke="{stroke}" stroke-width="{width:g}"/>')


def keyboard_svg(settings: Settings) -> list[str]:
    t = settings.theme
    first = Note.from_midi(settings.first_midi)
    whites = scale_notes(settings.first_midi, settings.last_midi)
    width = 924 / len(whites)
    parts = [rect(32, 76, 936, 192, t.black_key, 6)]
    for black in (False, True):
        for midi in range(settings.first_midi, settings.last_midi + 1):
            physical = Note.from_midi(midi)
            if physical.sharp != black:
                continue
            index = physical.staff_step() - first.staff_step()
            x = (38 + (index + 1) * width - width * 0.3 if black
                 else 38 + index * width)
            key_width, height = (width * 0.60, 112) if black else (width - 1, 180)
            note = settings.key.note(midi)
            attrs = (f' data-degree="{note.degree + 1}" data-color="{settings.colors[note.degree]}"'
                     if note is not None else '')
            parts.append(f'<g id="key-{midi}" data-midi="{midi}" '
                         f'data-black="{str(black).lower()}"{attrs}>')
            parts.append(f'<title>{note.name() if note is not None else physical.name()}</title>')
            parts.append(rect(x, 82, key_width, height, t.black_key if black else t.panel, 2))
            if note is not None:
                cx, cy = x + key_width / 2, 174 if black else 241
                fill = settings.colors[note.degree]
                parts.append(f'<circle cx="{cx:g}" cy="{cy:g}" r="10.5" fill="{fill}"/>')
                parts.append(pitch_label(cx, cy + 5, note.letter, note.accidental, 14))
            parts.append('</g>')
    return parts


def staff_y(note: Note | SpelledNote, clef: str) -> float:
    if clef not in ("treble", "bass"):
        raise ValueError("Unknown clef")
    bottom, reference = (178, 30) if clef == "treble" else (262, 18)
    return bottom - (note.staff_step() - reference) * 7


def ledger_lines(y: float, bottom: float, spacing: int = 20) -> tuple[float, ...]:
    top = bottom - 4 * spacing
    if y > bottom:
        return tuple(float(value) for value in range(int(bottom + spacing), int(y) + 1, spacing))
    if y < top:
        return tuple(float(value) for value in range(int(top - spacing), int(y) - 1, -spacing))
    return ()


def pitch_label(x: float, y: float, letter: str, accidental: int, size: int) -> str:
    """Uppercase pitch letters with explicit accidentals, fitted inside the dot."""
    if (letter not in "CDEFGAB" or len(letter) != 1
            or type(accidental) is not int or accidental not in (-1, 0, 1)):
        raise ValueError("Expected a note letter and flat/natural/sharp accidental")
    sign = {-1: "♭", 0: "", 1: "♯"}[accidental]
    return text(x, y, letter + sign, size - 3 if accidental else size,
                "#FFFFFF", "middle")


def key_signature_svg(key: MajorKey, clef: str, fill: str) -> list[str]:
    """Conventional signature order and staff positions, with font-free signs."""
    if clef not in ("treble", "bass"):
        raise ValueError("Unknown clef")
    accidentals = dict(zip(key.letters, key.accidentals))
    sharp = 1 in key.accidentals
    order = "FCGDAEB" if sharp else "BEADGCF"
    # Diatonic steps above the bottom line; bass signatures sit two steps lower.
    steps = (8, 5, 9, 6, 3, 7, 4) if sharp else (4, 7, 3, 6, 2, 5, 1)
    bottom = 178 if clef == "treble" else 262
    path = ("M-3 -12 V12 M3 -14 V10 M-6 -4 L6 -7 M-6 5 L6 2" if sharp else
            "M-3 -22 V5 C10 -1 7 -13 -3 -4")
    parts: list[str] = []
    for letter, step in zip(order, steps):
        if accidentals[letter] == 0:
            continue
        x = 1078 + len(parts) * 14
        y = bottom - (step - (2 if clef == "bass" else 0)) * 7
        sign = "♯" if sharp else "♭"
        parts.append(f'<g data-key-signature="{clef}" data-letter="{letter}" '
                     f'data-accidental="{accidentals[letter]}" '
                     f'transform="translate({x} {y})"><title>{letter}{sign}</title>'
                     f'<path d="{path}" fill="none" stroke="{fill}" '
                     f'stroke-width="2" stroke-linecap="round"/></g>')
    return parts


def staff_svg(settings: Settings, clefs: tuple[str, str]) -> list[str]:
    t = settings.theme
    parts: list[str] = []
    # Both clefs use the same diatonic coordinate system: C4 is y=192.
    for clef, bottom, notes, glyph in (
        ("treble", 178, settings.key.notes(60, settings.last_midi), clefs[0]),
        ("bass", 262, settings.key.notes(settings.first_midi, 59), clefs[1]),
    ):
        for i in range(5):
            parts.append(line(1032, bottom - i * 14, 1552, bottom - i * 14, t.line, 1.2))
        anchor_y = bottom - 14 if clef == "treble" else bottom - 42
        glyph_anchor = 170 if clef == "treble" else 566
        scale = 14 / 194
        parts.append(f'<path id="{clef}-clef" d="{glyph}" fill="{t.ink}" '
                     f'transform="translate(1027 {anchor_y + glyph_anchor * scale:g}) '
                     f'scale({scale:g} {-scale:g})"/>')
        signature = key_signature_svg(settings.key, clef, t.ink)
        parts.extend(signature)
        note_start = 1090 + len(signature) * 14
        for index, note in enumerate(notes):
            x = note_start + index * (1536 - note_start) / max(1, len(notes) - 1)
            y = staff_y(note, clef)
            fill = settings.colors[note.degree]
            parts.append(f'<g id="note-{note.midi}" data-midi="{note.midi}" '
                         f'data-degree="{note.degree + 1}" data-color="{fill}">'
                         f'<title>{note.name()} / degree {note.degree + 1}</title>')
            parts.extend(line(x - 15, ledger, x + 15, ledger, t.muted, 1.2)
                         for ledger in ledger_lines(y, bottom, 14))
            parts.append(f'<circle cx="{x:g}" cy="{y:g}" r="10.5" fill="{fill}"/>')
            parts.append(pitch_label(x, y + 4, note.letter, note.accidental, 12))
            parts.append('</g>')
    parts.extend([line(1032, 122, 1032, 262, t.muted, 1.5),
                  '<path d="M1023 122 C1010 133 1028 180 1016 192 '
                  'C1028 205 1010 252 1023 262" fill="none" '
                  f'stroke="{t.ink}" stroke-width="2.5"/>'])
    return parts


def guitar_positions(settings: Settings, anchor_string: int) -> tuple[tuple[int, int, SpelledNote], ...]:
    anchor = settings.anchor_frets[anchor_string]
    first = anchor - settings.frets_before_anchor
    last = anchor + settings.frets_after_anchor
    return tuple((row, fret, note) for row, pitch in enumerate(settings.tuning)
                 for fret in range(first, last + 1)
                 if (note := settings.key.note(pitch + fret)) is not None)


def fret_inlays(x: float, side_y: float, double_offset: float,
                fret: int, fill: str) -> list[str]:
    """Side dots below the fretboard; the two dots at 12 are horizontal."""
    if fret == 12:
        xs = (x - double_offset, x + double_offset)
    elif fret in (3, 5, 7, 9):
        xs = (x,)
    else:
        return []
    return [f'<circle data-inlay-fret="{fret}" cx="{cx:g}" cy="{side_y:g}" '
            f'r="3" fill="{fill}"/>' for cx in xs]


def guitar_svg(settings: Settings, panel: int, anchor_string: int) -> list[str]:
    t = settings.theme
    left, top = 16 + (panel % 3) * 528, 300 + (panel // 3) * 224
    anchor = settings.anchor_frets[anchor_string]
    first = anchor - settings.frets_before_anchor
    last = anchor + settings.frets_after_anchor
    grid_x, grid_y = left + 40, top + 32
    columns = last - first + 1
    width = 456 / columns
    parts = [rect(left, top, 512, 208, t.panel, 10)]
    for fret in range(first, last + 1):
        x = grid_x + (fret - first + 0.5) * width
        parts.append(text(x, grid_y - 19, str(fret), 12, t.muted, "middle"))
        parts.extend(fret_inlays(x, grid_y + 172, 5, fret, t.muted))
    for column in range(columns + 1):
        x = grid_x + column * width
        parts.append(line(x, grid_y, x, grid_y + 150, t.line))
    for row in range(len(settings.tuning)):
        y = grid_y + row * 30
        parts.append(line(grid_x, y, grid_x + 456, y, t.line, 1 + row * 0.16))
        parts.append(text(left + 24, y + 4, str(row + 1), 12, t.muted, "end"))
    for row, fret, note in guitar_positions(settings, anchor_string):
        x = grid_x + (fret - first + 0.5) * width
        y = grid_y + row * 30
        fill = settings.colors[note.degree]
        selected = row == anchor_string and fret == anchor
        parts.append(f'<g data-panel="{panel}" data-string="{row + 1}" data-fret="{fret}" '
                     f'data-midi="{note.midi}" data-degree="{note.degree + 1}" '
                     f'data-anchor="{str(selected).lower()}" data-color="{fill}">'
                     f'<title>{note.name()}</title>')
        if selected:
            parts.append(f'<circle cx="{x:g}" cy="{y:g}" r="18" fill="{t.panel}" '
                         f'stroke="{fill}" stroke-width="2"/>')
        parts.append(f'<circle cx="{x:g}" cy="{y:g}" r="13" fill="{fill}"/>')
        parts.append(pitch_label(x, y + 5, note.letter, note.accidental, 15))
        parts.append('</g>')
    return parts


def block_positions(settings: Settings) -> tuple[tuple[int, int, SpelledNote], ...]:
    block = settings.blocks
    result: list[tuple[int, int, SpelledNote]] = []
    for row in range(2):
        for offset in (0, 2, 3, 5):
            fret = block.first_fret + offset
            note = settings.key.note(settings.tuning[block.upper_string + row] + fret)
            if note is None:
                raise ValueError("Block position is outside the selected major scale")
            result.append((row, fret, note))
    return tuple(result)


def blocks_svg(settings: Settings) -> list[str]:
    """Two small adjacent blocks directly beneath the keyboard, at 2:1:2 spacing."""
    t, block = settings.theme, settings.blocks
    parts = [rect(100, 306, 324, 77, t.paper, 5),
             rect(424, 306, 324, 77, t.paper, 5)]
    for column in range(7):
        x = 100 + column * 108
        parts.append(line(x, 309, x, 378, t.line))
        if column < 6:
            parts.append(text(x + 54, 296, str(block.first_fret + column), 11, t.muted, "middle"))
    for row in range(2):
        y = 318 + row * 47
        parts.extend([line(100, y, 748, y, t.line, 1.5 + row * 0.3),
                      text(80, y + 5, str(block.upper_string + row + 1), 12, t.muted, "end")])
    for row, fret, note in block_positions(settings):
        x, y = 154 + (fret - block.first_fret) * 108, 318 + row * 47
        fill = settings.colors[note.degree]
        parts.extend([f'<g data-block="{0 if fret < block.first_fret + 3 else 1}" '
                      f'data-string="{block.upper_string + row + 1}" data-fret="{fret}" '
                      f'data-midi="{note.midi}" data-degree="{note.degree + 1}" '
                      f'data-color="{fill}"><title>{note.name()}</title>',
                      f'<circle cx="{x}" cy="{y}" r="16" fill="{fill}"/>',
                      pitch_label(x, y + 6, note.letter, note.accidental, 18), '</g>'])
    return parts


def tile_parts(settings: Settings, clefs: tuple[str, str]) -> list[str]:
    t = settings.theme
    parts = [f'<g transform="translate(0 -52)" font-family="{escape(settings.text_font, quote=True)}">',
             rect(16, 60, 968, 224, t.panel, 10),
             rect(1000, 60, 584, 224, t.panel, 10)]
    parts.extend(keyboard_svg(settings))
    parts.extend(staff_svg(settings, clefs))
    for panel, anchor_string in enumerate((5, 4, 3, 2, 1, 0)):
        parts.extend(guitar_svg(settings, panel, anchor_string))
    parts.append('</g>')
    return parts


def svg_start(width: int, height: int, title: str, paper: str) -> list[str]:
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title>',
            '<desc id="desc">大调音阶的钢琴、五线谱、吉他指板统一对照。'
            '彩色圆点表示调内音，1 红、2/3 绿、4/5 鲑鱼色、6/7 蓝。'
            '音名大写，升降音使用 ♯/♭；以实际音高对应，中央 C 对齐。</desc>',
            rect(0, 0, width, height, paper)]


def render_svg(settings: Settings, clefs: tuple[str, str]) -> str:
    parts = svg_start(1600, 696, settings.title, settings.theme.paper)
    parts.extend(tile_parts(settings, clefs))
    return '\n'.join(parts + ['</svg>']) + '\n'


def overview_heading(settings: Settings) -> list[str]:
    key = settings.key
    name = key.name.replace('b', '♭').replace('#', '♯')
    parts = [text(16, 29, name, 28, settings.theme.ink, weight=600)]
    for degree, (letter, accidental) in enumerate(zip(key.letters, key.accidentals)):
        x = 164 + degree * 42
        parts.append(f'<circle cx="{x}" cy="21" r="13" fill="{settings.colors[degree]}"/>')
        parts.append(pitch_label(x, 26, letter, accidental, 15))
    return parts


def render_overview(settings: Settings, clefs: tuple[str, str], *, stacked: bool = False) -> str:
    overview = replace(settings.overview, columns=1, rows=12) if stacked else settings.overview
    tile_width, tile_height = 1600, 740
    width = overview.columns * tile_width + (overview.columns + 1) * overview.gap
    height = overview.rows * tile_height + (overview.rows + 1) * overview.gap
    parts = svg_start(width, height, '十二大调 · 钢琴 / 五线谱 / 吉他', settings.theme.paper)
    parts.append(f'<g font-family="{escape(settings.text_font, quote=True)}">')
    for index, key in enumerate(overview.keys):
        config = transpose_settings(settings, key)
        x = overview.gap + (index % overview.columns) * (tile_width + overview.gap)
        y = overview.gap + (index // overview.columns) * (tile_height + overview.gap)
        parts.append(f'<g data-key="{key.name}" transform="translate({x} {y})">')
        parts.extend(overview_heading(config))
        markup = '\n'.join(tile_parts(config, clefs))
        markup = re.sub(r'\bid="([^"]+)"', lambda match: f'id="key{index}-{match[1]}"', markup)
        parts.extend(['<g transform="translate(0 44)">', markup, '</g></g>'])
    return '\n'.join(parts + ['</g></svg>']) + '\n'


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=root / "config/c-major-atlas.toml")
    parser.add_argument("--output", type=Path)
    layout = parser.add_mutually_exclusive_group()
    layout.add_argument("--all-keys", action="store_true", help="Render the configured 12-major-key grid")
    layout.add_argument("--stacked", action="store_true", help="Render all 12 keys in one mobile column")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output")
    args = parser.parse_args()
    try:
        with args.config.open("rb") as stream:
            settings = parse_settings(tomllib.load(stream), args.config.parent)
        clefs = load_clefs(settings.music_font)
        svg = (render_overview(settings, clefs, stacked=args.stacked)
               if args.all_keys or args.stacked else render_svg(settings, clefs))
        if args.output is None:
            name = ("major-scales-atlas-mobile.svg" if args.stacked else
                    "major-scales-atlas.svg" if args.all_keys else "c-major-atlas.svg")
            args.output = root / "scripts" / name
        if args.output.suffix.lower() != ".svg":
            raise ValueError("Output must have an .svg extension")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w" if args.force else "x", encoding="utf-8") as stream:
            stream.write(svg)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"error: {error}\n")
    print(args.output)


if __name__ == "__main__":
    main()
