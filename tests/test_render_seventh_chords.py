"""Chord spelling, chord-relative colors, complete coverage and reused geometry."""

from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as ET

from hypothesis import given, strategies as st
import pytest

from scripts import render_key_atlas as atlas
from scripts.render_seventh_chords import (
    Chord, Settings, diatonic_chords, guitar, keyboard, load_settings,
    render_guitar, render_keyboard, tone_color,
)


@pytest.fixture
def settings() -> Settings:
    return load_settings(Path('config/seventh-chords.toml'))


@pytest.mark.parametrize('root,quality,names', [
    ('C', 0, ['C', 'E', 'G', 'B']),
    ('C', 1, ['C', 'E♭', 'G', 'B♭']),
    ('C', 2, ['C', 'E', 'G', 'B♭']),
    ('C', 3, ['C', 'E♭', 'G♭', 'B♭']),
    ('C', 4, ['C', 'E♭', 'G♭', 'B♭♭']),
    ('Gb', 4, ['G♭', 'B♭♭', 'D♭♭', 'F♭♭']),
    ('B', 0, ['B', 'D♯', 'F♯', 'A♯']),
])
def test_chord_spellings(settings: Settings, root: str, quality: int, names: list[str]) -> None:
    chord = Chord.build(root, settings.kinds[quality])
    assert [tone.name for tone in chord.tones] == names
    assert [tone.role for tone in chord.tones] == [0, 1, 2, 3]
    assert len({tone.pitch_class for tone in chord.tones}) == 4


def test_every_spelling_roundtrips_and_roles_are_chord_relative(settings: Settings) -> None:
    for root in settings.roots:
        for kind in settings.kinds:
            chord = Chord.build(root, kind)
            for tone, color in zip(chord.tones, ('#CE303A', '#258448', '#E86568', '#1649E8'), strict=True):
                natural = (0, 2, 4, 5, 7, 9, 11)['CDEFGAB'.index(tone.name[0])]
                accidental = tone.name.count('♯') - tone.name.count('♭')
                assert (natural + accidental) % 12 == tone.pitch_class
                assert tone_color(tone, settings) == color
    # D is degree 2 in C major, but must be red as the root of Dm7.
    dm7 = diatonic_chords('C', settings)[1]
    assert dm7.tones[0].name == 'D'
    assert tone_color(dm7.tones[0], settings) == '#CE303A'


@pytest.mark.parametrize('key,names', [
    ('C', ['Cmaj7', 'Dm7', 'Em7', 'Fmaj7', 'G7', 'Am7', 'Bm7♭5']),
    ('G', ['Gmaj7', 'Am7', 'Bm7', 'Cmaj7', 'D7', 'Em7', 'F♯m7♭5']),
])
def test_diatonic_chords(settings: Settings, key: str, names: list[str]) -> None:
    chords = diatonic_chords(key, settings)
    assert [chord.name() for chord in chords] == names
    pcs = set(atlas.MajorKey.from_name(key).pitch_classes)
    assert all({tone.pitch_class for tone in chord.tones} <= pcs for chord in chords)


def test_keyboard_has_sixty_chords_and_no_staff(settings: Settings) -> None:
    root = ET.fromstring(render_keyboard(settings))
    cards = root.findall('.//{*}g[@data-chord]')
    assert len(cards) == 60
    assert len({card.attrib['data-chord'] for card in cards}) == 60
    assert root.findall('.//{*}path') == []
    for card, chord in zip(cards, (Chord.build(r, k) for r in settings.roots for k in settings.kinds), strict=True):
        keys = card.findall('.//{*}g[@data-midi]')
        assert len(keys) == settings.base.last_midi - settings.base.first_midi + 1
        assert {int(node.attrib['data-midi']) for node in keys if 'data-role' in node.attrib} == {
            midi for midi in range(settings.base.first_midi, settings.base.last_midi + 1)
            if chord.tone(midi) is not None
        }
        for node in keys:
            midi = int(node.attrib['data-midi'])
            tone = chord.tone(midi)
            if tone is None:
                assert node.find('{*}circle') is None
            else:
                assert node.attrib['data-color'] == tone_color(tone, settings)
                assert node.findtext('{*}text') == tone.name
                assert int(node.attrib['data-role']) == tone.role


def test_keyboard_reuses_physical_key_dimensions(settings: Settings) -> None:
    original = ET.fromstring('<g>' + ''.join(atlas.keyboard_svg(settings.base, full_width=True)) + '</g>')
    rendered = ET.fromstring(keyboard(Chord.build('C', settings.kinds[0]), settings))
    old = original.findall('.//g[@data-midi]/rect')
    new = rendered.findall('.//g[@data-midi]/rect')
    assert [node.attrib for node in new] == [node.attrib for node in old]
    assert rendered.attrib['transform'] == 'translate(-278 -36)'
    border = rendered.find('.//rect[@data-keyboard]')
    assert border is not None and border.attrib['width'] == '730'


def test_guitar_has_one_example_per_quality(settings: Settings) -> None:
    root = ET.fromstring(render_guitar(settings))
    cards = root.findall('.//{*}g[@data-chord]')
    chords = tuple(Chord.build(root, kind) for root, kind in zip(
        ('G', 'A', 'D', 'F#', 'C'), settings.kinds, strict=True))
    assert len(cards) == len(chords) == 5
    assert [card.attrib['data-chord'] for card in cards] == [
        'Gmaj7', 'Am7', 'D7', 'F♯m7♭5', 'Cdim7',
    ]
    assert root.findall('.//{*}path') == []
    for index, (card, chord) in enumerate(zip(cards, chords, strict=True)):
        nodes = card.findall('.//{*}g[@data-fret]')
        actual = [(int(node.attrib['data-string']), int(node.attrib['data-fret'])) for node in nodes]
        expected = {(row + 1, fret) for row, pitch in enumerate(settings.base.tuning)
                    for fret in range(1, 18) if chord.tone(pitch + fret) is not None}
        assert len(actual) == len(set(actual))
        assert set(actual) == expected
        for node in nodes:
            tone = chord.tone(int(node.attrib['data-midi']))
            assert tone is not None
            assert node.findtext('{*}text') == tone.degree
            assert node.attrib['data-color'] == tone_color(tone, settings, diminished_pairs=index == 4)
        lines = card.findall('.//{*}line')
        strings = [line for line in lines if line.attrib['y1'] == line.attrib['y2']]
        assert len(strings) == 6
        assert all(float(line.attrib['x2']) - float(line.attrib['x1']) == 952 for line in strings)
        assert len(lines) - len(strings) == 18
        assert len(card.findall('.//*[@data-inlay-fret="12"]')) == 2


@pytest.mark.parametrize('instrument', ['keyboard', 'guitar'])
def test_no_visible_headings_legends_or_explanations(settings: Settings, instrument: str) -> None:
    svg = render_keyboard(settings) if instrument == 'keyboard' else render_guitar(settings)
    root = ET.fromstring(svg)
    content = root.find('{*}g')
    assert content is not None
    assert all('data-chord' in child.attrib for child in content)
    for card in content:
        assert [text.text for text in card.findall('{*}text')] == (
            [card.attrib['data-chord']] if instrument == 'keyboard' else []
        )
        if instrument == 'guitar':
            assert all((text.text or '').replace('♭', '').isdigit()
                       for text in card.findall('.//{*}text'))
    assert all('data-chord' not in node.attrib or 'data-caption' not in node.attrib for node in root.iter())


def test_diminished_pair_colors_and_degrees(settings: Settings) -> None:
    chord = Chord.build('C', settings.kinds[-1])
    assert [tone.degree for tone in chord.tones] == ['1', '♭3', '♭5', '♭♭7']
    assert [tone_color(tone, settings, diminished_pairs=True) for tone in chord.tones] == [
        '#E86568', '#1649E8', '#E86568', '#1649E8',
    ]
    assert {(tone.pitch_class + 3) % 12 for tone in chord.tones} == {
        tone.pitch_class for tone in chord.tones
    }


@given(st.integers(0, 11), st.integers(0, 4))
def test_chord_positions_repeat_after_twelve_frets(root_index: int, quality: int) -> None:
    config = load_settings(Path('config/seventh-chords.toml'))
    chord = Chord.build(config.roots[root_index], config.kinds[quality])
    for pitch in config.base.tuning:
        for fret in range(1, 6):
            assert chord.tone(pitch + fret) == chord.tone(pitch + fret + 12)


def test_guitar_dots_do_not_overlap_or_clip(settings: Settings) -> None:
    for key in settings.guitar_keys:
        for chord in diatonic_chords(key, settings):
            root = ET.fromstring(guitar(chord, settings))
            for circle in root.findall('.//g[@data-midi]/circle'):
                x, y, radius = (float(circle.attrib[attr]) for attr in ('cx', 'cy', 'r'))
                assert 16 <= x - radius < x + radius <= settings.base.canvas_width - 16
                assert 8 <= y - radius < y + radius <= 216
                assert 2 * radius < 30


@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_cli_writes_two_pngs_and_protects_all_outputs(tmp_path: Path, theme: str) -> None:
    command = [sys.executable, 'scripts/render_seventh_chords.py', '--output', str(tmp_path),
               '--theme', theme]
    first = subprocess.run(command, capture_output=True, text=True, check=False)
    assert first.returncode == 0, first.stderr
    paths = sorted(tmp_path.iterdir())
    assert len(paths) == 4
    suffix = '-dark' if theme == 'dark' else ''
    assert {path.name for path in paths} == {
        f'seventh-chords-{instrument}{suffix}.{extension}'
        for instrument in ('keyboard', 'guitar') for extension in ('svg', 'png')
    }
    original = {path: path.read_bytes() for path in paths}
    assert all(path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') for path in tmp_path.glob('*.png'))
    second = subprocess.run(command, capture_output=True, text=True, check=False)
    assert second.returncode == 2
    assert {path: path.read_bytes() for path in paths} == original
    forced = subprocess.run(command + ['--force'], capture_output=True, text=True, check=False)
    assert forced.returncode == 0, forced.stderr
    assert {path: path.read_bytes() for path in paths} == original


@pytest.mark.parametrize('instrument', ['keyboard', 'guitar'])
def test_themes_preserve_content_and_geometry_with_readable_colors(instrument: str) -> None:
    render = render_keyboard if instrument == 'keyboard' else render_guitar
    light = load_settings(Path('config/seventh-chords.toml'))
    dark = load_settings(Path('config/seventh-chords.toml'), theme_name='dark')
    assert dark.base.theme.black_key == '#FFFFFF'
    assert dark.base.theme.white_key == '#000000'
    assert light.base.theme.white_key == '#FFFFFF'
    light_root, dark_root = ET.fromstring(render(light)), ET.fromstring(render(dark))
    assert light_root.attrib == dark_root.attrib
    for root, config, background in ((light_root, light, '#FFFFFF'), (dark_root, dark, '#000000')):
        paper = root.find('{*}rect')
        assert paper is not None and paper.attrib['fill'] == background
        assert all(line.attrib['stroke'] == config.base.theme.line for line in root.findall('.//{*}line'))
        for card in root.findall('.//{*}g[@data-chord]'):
            pair_colors = instrument == 'guitar' and card.attrib['data-chord'] == 'Cdim7'
            for note in card.findall('.//{*}g[@data-role]'):
                role = int(note.attrib['data-role'])
                index = (3 if role % 2 == 0 else 5) if pair_colors else (0, 1, 3, 5)[role]
                assert note.attrib['data-color'] == config.base.colors[index]
        for key in root.findall('.//{*}g[@data-midi]'):
            body = key.find('{*}rect')
            if body is not None:
                midi = int(key.attrib['data-midi'])
                assert body.attrib['fill'] == (config.base.theme.black_key if atlas.Note.from_midi(midi).sharp
                                                else config.base.theme.white_key)
    for a, b in zip(light_root.iter(), dark_root.iter(), strict=True):
        assert a.tag == b.tag and a.text == b.text
        assert {k: v for k, v in a.attrib.items() if k not in ('fill', 'stroke', 'data-color')} == {
            k: v for k, v in b.attrib.items() if k not in ('fill', 'stroke', 'data-color')
        }


def test_reject_unknown_theme() -> None:
    with pytest.raises(ValueError, match='Theme must be light or dark'):
        load_settings(Path('config/seventh-chords.toml'), theme_name='sepia')
