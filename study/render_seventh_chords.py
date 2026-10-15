"""Render separate seventh-chord keyboard and guitar atlases, without staves."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html import escape
from pathlib import Path
import subprocess
import tomllib
from xml.etree import ElementTree as ET

if __package__:
    from . import render_key_atlas as atlas
else:
    import render_key_atlas as atlas


@dataclass(frozen=True)
class ChordKind:
    name: str
    suffix: str
    intervals: tuple[int, ...]


@dataclass(frozen=True)
class Tone:
    pitch_class: int
    name: str
    degree: str
    role: int


@dataclass(frozen=True)
class Chord:
    root: str
    kind: ChordKind
    tones: tuple[Tone, ...]

    @classmethod
    def build(cls, root: str, kind: ChordKind) -> Chord:
        key = atlas.MajorKey.from_name(root)
        tones: list[Tone] = []
        for role, (step, interval, natural_interval) in enumerate(
            zip((0, 2, 4, 6), kind.intervals, (0, 4, 7, 11), strict=True)
        ):
            pc = (key.pitch_classes[0] + interval) % 12
            letter = key.letters[step]
            natural = (0, 2, 4, 5, 7, 9, 11)['CDEFGAB'.index(letter)]
            accidental = (pc - natural + 6) % 12 - 6
            if not -2 <= accidental <= 2:
                raise ValueError('Chord spelling requires more than a double accidental')
            sign = {-2: '♭♭', -1: '♭', 0: '', 1: '♯', 2: '♯♯'}[accidental]
            alteration = interval - natural_interval
            if alteration not in (-2, -1, 0):
                raise ValueError('Unsupported chord-tone alteration')
            degree = '♭' * -alteration + str(step + 1)
            tones.append(Tone(pc, letter + sign, degree, role))
        return cls(root, kind, tuple(tones))

    def name(self) -> str:
        return self.root.replace('b', '♭').replace('#', '♯') + self.kind.suffix

    def tone(self, midi: int) -> Tone | None:
        return next((tone for tone in self.tones if tone.pitch_class == midi % 12), None)


@dataclass(frozen=True)
class Settings:
    base: atlas.Settings
    roots: tuple[str, ...]
    guitar_keys: tuple[str, ...]
    diminished_root: str
    kinds: tuple[ChordKind, ...]
    margin: int
    gap: int
    keyboard_card_height: int
    guitar_card_height: int


def string_array(value: object, count: int) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) != count:
        raise ValueError(f'Expected {count} strings')
    return tuple(atlas.nonempty_text(item) for item in value)


def load_settings(path: Path, *, theme_name: str = 'light') -> Settings:
    with path.open('rb') as stream:
        raw = tomllib.load(stream)
    source = path.parent / atlas.nonempty_text(raw['atlas_config'])
    with source.open('rb') as stream:
        base = atlas.parse_settings(tomllib.load(stream), source.parent, theme_name=theme_name)
    roots = string_array(raw['roots'], 12)
    if len({atlas.MajorKey.from_name(root).pitch_classes[0] for root in roots}) != 12:
        raise ValueError('Keyboard roots must cover all twelve pitch classes')
    keys = string_array(raw['guitar_keys'], 1)
    atlas.MajorKey.from_name(keys[0])
    diminished = atlas.nonempty_text(raw['diminished_root'])
    atlas.MajorKey.from_name(diminished)
    entries = raw['chords']
    expected = ((0, 4, 7, 11), (0, 3, 7, 10), (0, 4, 7, 10), (0, 3, 6, 10), (0, 3, 6, 9))
    if not isinstance(entries, list) or len(entries) != len(expected):
        raise ValueError('Provide major, minor, dominant, half-diminished and diminished sevenths')
    kinds: list[ChordKind] = []
    for entry, intervals in zip(entries, expected, strict=True):
        if not isinstance(entry, dict) or not isinstance(entry.get('intervals'), list):
            raise ValueError('Expected a chord table with four semitone intervals')
        parsed = tuple(atlas.bounded_integer(v, 0, 11) for v in entry['intervals'])
        if parsed != intervals:
            raise ValueError('Chord intervals or quality order are incorrect')
        kinds.append(ChordKind(atlas.nonempty_text(entry['name']),
                               atlas.nonempty_text(entry['suffix']), parsed))
    return Settings(base, roots, keys, diminished, tuple(kinds),
                    atlas.bounded_integer(raw['margin'], 16, 100),
                    atlas.bounded_integer(raw['gap'], 8, 100),
                    atlas.bounded_integer(raw['keyboard_card_height'], 244, 500),
                    atlas.bounded_integer(raw['guitar_card_height'], 232, 500))


def tone_color(tone: Tone, settings: Settings, *, diminished_pairs: bool = False) -> str:
    colors = settings.base.colors
    if diminished_pairs:
        return colors[3] if tone.role % 2 == 0 else colors[5]
    return colors[(0, 1, 3, 5)[tone.role]]


def tone_dot(x: float, y: float, radius: float, tone: Tone, settings: Settings,
             *, guitar: bool, diminished_pairs: bool = False) -> str:
    value = tone.degree if guitar else tone.name
    size = (14 if len(value) == 1 else 10) if guitar else (11 if len(value) == 1 else 8)
    fill = tone_color(tone, settings, diminished_pairs=diminished_pairs)
    return (f'<circle cx="{x:g}" cy="{y:g}" r="{radius:g}" fill="{fill}"/>'
            + atlas.text(x, y + 4, value, size, '#FFFFFF', 'middle'))


def keyboard(chord: Chord, settings: Settings) -> str:
    # Reuse the existing physical keys at their exact sizes; replace scale dots.
    root = ET.fromstring('<g>' + ''.join(atlas.keyboard_svg(settings.base, full_width=True)) + '</g>')
    for group in root.findall('g[@data-midi]'):
        midi = int(group.attrib['data-midi'])
        physical = group.find('rect')
        if physical is None:
            raise ValueError('Keyboard renderer did not provide a physical key')
        group.clear()
        group.set('data-midi', str(midi))
        group.append(physical)
        tone = chord.tone(midi)
        if tone is None:
            continue
        group.set('data-role', str(tone.role))
        group.set('data-color', tone_color(tone, settings))
        x = float(physical.attrib['x']) + float(physical.attrib['width']) / 2
        y = 174 if atlas.Note.from_midi(midi).sharp else 241
        ET.SubElement(group, 'title').text = f'{tone.name} / {tone.degree}'
        dot = ET.fromstring('<g>' + tone_dot(x, y, 8.5, tone, settings, guitar=False) + '</g>')
        group.extend(dot)
    return '<g transform="translate(-278 -36)">' + ET.tostring(root, encoding='unicode') + '</g>'


def guitar(chord: Chord, settings: Settings, *, diminished_pairs: bool = False) -> str:
    base = settings.base
    root = ET.fromstring('<g>' + ''.join(atlas.fretboard_svg(
        base, base.first_fret, base.last_fret, 16, 8, base.canvas_width - 88, 0, None)) + '</g>')
    for group in root.findall('g[@data-midi]'):
        root.remove(group)
    width = (base.canvas_width - 88) / (base.last_fret - base.first_fret + 1)
    for row, pitch in enumerate(base.tuning):
        for fret in range(base.first_fret, base.last_fret + 1):
            tone = chord.tone(pitch + fret)
            if tone is None:
                continue
            group = ET.SubElement(root, 'g', {'data-string': str(row + 1), 'data-fret': str(fret),
                                             'data-midi': str(pitch + fret), 'data-role': str(tone.role),
                                             'data-degree': tone.degree,
                                             'data-color': tone_color(tone, settings, diminished_pairs=diminished_pairs)})
            ET.SubElement(group, 'title').text = f'{tone.name} / {tone.degree}'
            x, y = 56 + (fret - base.first_fret + 0.5) * width, 40 + row * 30
            dot = ET.fromstring('<g>' + tone_dot(x, y, 13, tone, settings, guitar=True,
                                                diminished_pairs=diminished_pairs) + '</g>')
            group.extend(dot)
    return ET.tostring(root, encoding='unicode')


def card(chord: Chord, settings: Settings, x: float, y: float,
         *, instrument: str, diminished_pairs: bool = False) -> str:
    body = (keyboard(chord, settings) if instrument == 'keyboard' else
            guitar(chord, settings, diminished_pairs=diminished_pairs))
    heading = (atlas.text(16, 25, chord.name(), 20, settings.base.theme.ink, weight=600)
               if instrument == 'keyboard' else '')
    return (f'<g data-chord="{escape(chord.name(), quote=True)}" '
            f'data-instrument="{instrument}" transform="translate({x:g} {y:g})">'
            + heading + body + '</g>')


def document_start(width: int, height: int, title: str, subtitle: str, settings: Settings) -> list[str]:
    # Accessible metadata only; no visible headings, legend or explanatory text.
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle)}</desc>',
            atlas.rect(0, 0, width, height, settings.base.theme.paper),
            f'<g font-family="{escape(settings.base.text_font, quote=True)}">']


def render_keyboard(settings: Settings) -> str:
    width = settings.base.canvas_width - 310
    total_width = 2 * settings.margin + 5 * width + 4 * settings.gap
    total_height = 2 * settings.margin + 12 * settings.keyboard_card_height + 11 * settings.gap
    parts = document_start(total_width, total_height, '十二根音 · 五类七和弦 · 键盘',
                           '每行一个根音；每列一种和弦。仅标和弦音，颜色按当前和弦的 1 / 3 / 5 / 7；键位范围 F2–C6。', settings)
    for row, root in enumerate(settings.roots):
        for column, kind in enumerate(settings.kinds):
            chord = Chord.build(root, kind)
            parts.append(card(chord, settings, settings.margin + column * (width + settings.gap),
                              settings.margin + row * (settings.keyboard_card_height + settings.gap),
                              instrument='keyboard'))
    return '\n'.join(parts + ['</g></svg>']) + '\n'


def diatonic_chords(key_name: str, settings: Settings) -> tuple[Chord, ...]:
    key = atlas.MajorKey.from_name(key_name)
    result: list[Chord] = []
    for degree in range(7):
        pcs = tuple(key.pitch_classes[(degree + step) % 7] for step in (0, 2, 4, 6))
        intervals = tuple((pc - pcs[0]) % 12 for pc in pcs)
        kind = next((kind for kind in settings.kinds if kind.intervals == intervals), None)
        if kind is None:
            raise ValueError('No matching quality for a diatonic seventh chord')
        accidental = {-1: 'b', 0: '', 1: '#'}[key.accidentals[degree]]
        result.append(Chord.build(key.letters[degree] + accidental, kind))
    return tuple(result)


def render_guitar(settings: Settings) -> str:
    total_width = 2 * settings.margin + settings.base.canvas_width
    key_name = settings.guitar_keys[0]
    diatonic = diatonic_chords(key_name, settings)
    chords = tuple(next(chord for chord in diatonic if chord.kind == kind)
                   for kind in settings.kinds[:-1])
    chords += (Chord.build(settings.diminished_root, settings.kinds[-1]),)
    total_height = (2 * settings.margin + len(chords) * settings.guitar_card_height
                    + (len(chords) - 1) * settings.gap)
    parts = document_start(total_width, total_height, '五类七和弦 · 吉他指板',
                           '1–17 品；级数与颜色相对于和弦根音。独立 dim7 使用两色交替。', settings)
    for row, chord in enumerate(chords):
        parts.append(card(chord, settings, settings.margin,
                          settings.margin + row * (settings.guitar_card_height + settings.gap),
                          instrument='guitar', diminished_pairs=chord.kind == settings.kinds[-1]))
    return '\n'.join(parts + ['</g></svg>']) + '\n'


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=root / 'config/seventh-chords.toml')
    parser.add_argument('--output', type=Path, default=root / 'scripts')
    parser.add_argument('--theme', choices=('light', 'dark'), default='light')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    try:
        settings = load_settings(args.config, theme_name=args.theme)
        suffix = '-dark' if args.theme == 'dark' else ''
        outputs = ((args.output / f'seventh-chords-keyboard{suffix}.svg', render_keyboard(settings)),
                   (args.output / f'seventh-chords-guitar{suffix}.svg', render_guitar(settings)))
        for path, _ in outputs:
            for target in (path, path.with_suffix('.png')):
                if target.exists() and not args.force:
                    raise FileExistsError(f'{target} exists; use --force')
        args.output.mkdir(parents=True, exist_ok=True)
        for path, svg in outputs:
            path.write_text(svg, encoding='utf-8')
            subprocess.run(['rsvg-convert', str(path), '-o', str(path.with_suffix('.png'))], check=True)
            print(path.with_suffix('.png'))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(2, f'error: {error}\n')


if __name__ == '__main__':
    main()
