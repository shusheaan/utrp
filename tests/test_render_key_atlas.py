"""Musical alignment and shared-color checks for the C-major atlas."""

from dataclasses import replace
from itertools import combinations
from math import hypot
from pathlib import Path
import subprocess
import sys
import tomllib
from xml.etree import ElementTree as ET

from hypothesis import given, strategies as st
import pytest

from scripts.render_key_atlas import (
    MajorKey, Note, Settings, block_positions, blocks_svg, fret_inlays, guitar_positions, guitar_svg,
    key_signature_svg, ledger_lines, parse_settings, render_svg, staff_svg,
    pitch_label, render_overview, scale_notes, staff_y, transpose_settings,
)


def settings(theme: str = "light") -> Settings:
    path = Path("config/c-major-atlas.toml")
    with path.open("rb") as stream:
        return parse_settings(tomllib.load(stream), path.parent, theme_name=theme)


def test_keyboard_range_and_scale() -> None:
    config = settings()
    notes = scale_notes(config.first_midi, config.last_midi)
    assert len(notes) == 26
    assert notes[0].name() == "F2"
    assert notes[-1].name() == "C6"
    assert notes[0].degree == 3
    assert config.last_midi - config.first_midi == 43
    assert {n.midi % 12 for n in notes} == {0, 2, 4, 5, 7, 9, 11}


@given(st.integers(0, 115))
def test_octaves_preserve_degree(midi: int) -> None:
    lower, upper = Note.from_midi(midi), Note.from_midi(midi + 12)
    assert lower.degree == upper.degree
    assert lower.sharp == upper.sharp
    assert upper.staff_step() - lower.staff_step() == 7


@pytest.mark.parametrize("midi,clef,y", [
    (60, "treble", 192), (64, "treble", 178), (67, "treble", 164),
    (77, "treble", 122), (84, "treble", 94),
    (41, "bass", 269), (43, "bass", 262), (53, "bass", 220),
    (57, "bass", 206),
])
def test_staff_landmarks(midi: int, clef: str, y: int) -> None:
    assert staff_y(Note.from_midi(midi), clef) == y


@pytest.mark.parametrize("name,letters,accidental", [
    ("C", "", 0), ("G", "F", 1), ("D", "FC", 1),
    ("A", "FCG", 1), ("E", "FCGD", 1), ("B", "FCGDA", 1),
    ("F#", "FCGDAE", 1), ("C#", "FCGDAEB", 1),
    ("F", "B", -1), ("Bb", "BE", -1), ("Eb", "BEA", -1),
    ("Ab", "BEAD", -1), ("Db", "BEADG", -1),
    ("Gb", "BEADGC", -1), ("Cb", "BEADGCF", -1),
])
@pytest.mark.parametrize("clef", ["treble", "bass"])
def test_key_signatures_have_standard_order_positions_and_clearance(
    name: str, letters: str, accidental: int, clef: str,
) -> None:
    config = transpose_settings(settings(), MajorKey.from_name(name))
    root = ET.fromstring('<svg>' + ''.join(staff_svg(config, ('M0 0', 'M0 0'))) + '</svg>')
    marks = root.findall(f'.//g[@data-key-signature="{clef}"]')
    assert ''.join(mark.attrib['data-letter'] for mark in marks) == letters
    expected_y = ((60, 93, 49, 82, 115, 71, 104) if accidental == 1
                  else (104, 71, 115, 82, 126, 93, 137))
    for index, mark in enumerate(marks):
        assert mark.attrib['data-accidental'] == str(accidental)
        y = expected_y[index] + (154 if clef == 'bass' else 0)
        assert mark.attrib['transform'] == f'translate({94 + index * 14} {y})'
        assert mark.find('path') is not None  # No music-font fallback needed.
    notes = root.findall('.//g[@data-midi]/circle')
    xs = [float(note.attrib['cx']) for note in notes]
    assert set(xs) == {214, 238}
    if marks:
        assert min(xs) - 15 > 94 + (len(marks) - 1) * 14 + 7


def test_signature_rejects_unknown_clef() -> None:
    with pytest.raises(ValueError, match="Unknown clef"):
        key_signature_svg(MajorKey.from_name('G'), 'alto', '#24323D')


def test_ledger_lines() -> None:
    assert ledger_lines(440, 420) == (440,)
    assert ledger_lines(300, 420) == (320, 300)
    assert ledger_lines(710, 700) == ()


def test_guitar_anchors_and_full_local_scale() -> None:
    config = settings()
    for string, fret in enumerate(config.anchor_frets):
        positions = guitar_positions(config, string)
        anchors = [(row, f, n) for row, f, n in positions if row == string and f == fret]
        assert len(anchors) == 1
        assert anchors[0][2].letter == "C"
        expected = {(row, f) for row, pitch in enumerate(config.tuning)
                    for f in range(fret - 2, fret + 5)
                    if (pitch + f) % 12 in (0, 2, 4, 5, 7, 9, 11)}
        assert {(row, f) for row, f, _ in positions} == expected


def test_all_views_share_degree_colors_and_staff_coverage() -> None:
    config = settings()
    root = ET.fromstring(render_svg(config, ("M0 0", "M0 0")))
    for node in root.findall('.//*[@data-degree]'):
        degree = int(node.attrib["data-degree"])
        assert node.attrib["data-color"] == config.colors[degree - 1]
    notes = {int(node.attrib["data-midi"]) for node in root.findall('.//{*}g')
             if node.attrib.get("id", "").startswith("note-")}
    assert notes == {note.midi for note in scale_notes(41, 84)}
    assert len(root.findall('.//*[@data-anchor="true"]')) == 6
    assert len(root.findall('.//{*}g[@data-black="true"]')) == 18


def test_requested_shared_color_groups() -> None:
    colors = settings().colors
    assert colors[0] == "#CE303A"  # C tonic.
    assert colors[1] == colors[2] == "#258448"  # D, E / degrees 2, 3.
    assert colors[3] == colors[4] == "#E86568"  # F, G.
    assert colors[5] == colors[6] == "#1649E8"  # A, B.
    assert len(set(colors)) == 4


def test_backgrounds_are_uniform_white_in_all_layouts() -> None:
    config = settings()
    assert config.theme.paper == config.theme.panel == '#FFFFFF'
    clefs = ('M0 0', 'M0 0')
    for svg in (render_svg(config, clefs), render_overview(config, clefs),
                render_overview(config, clefs, stacked=True)):
        root = ET.fromstring(svg)
        background = root.find('{*}rect')
        assert background is not None
        assert background.attrib['fill'] == '#FFFFFF'
        for card in root.findall('.//{*}rect[@rx="10"]'):
            assert card.attrib['fill'] == '#FFFFFF'
            assert 'stroke' not in card.attrib


@pytest.mark.parametrize("fret,count", [
    (0, 0), (1, 0), (2, 0), (3, 1), (4, 0), (5, 1), (6, 0),
    (7, 1), (8, 0), (9, 1), (10, 0), (11, 0), (12, 2),
    (13, 0), (14, 0), (15, 1), (16, 0), (17, 1), (18, 0),
    (19, 1), (20, 0), (21, 1), (22, 0), (23, 0), (24, 0),
])
def test_standard_fret_inlays(fret: int, count: int) -> None:
    marks = [ET.fromstring(part) for part in fret_inlays(100, 200, 30, fret, "#000000", 4)]
    assert len(marks) == count
    assert all(mark.attrib["data-inlay-fret"] == str(fret) for mark in marks)
    assert all(float(mark.attrib["cy"]) == 200 for mark in marks)
    assert all(mark.attrib["fill"] == "#000000" and mark.attrib["r"] == "4" for mark in marks)
    if count == 2:
        assert [float(mark.attrib["cx"]) for mark in marks] == [70, 130]


def test_inlays_render_in_all_visible_fret_windows() -> None:
    config = settings()
    root = ET.fromstring(render_svg(config, ("M0 0", "M0 0")))
    windows = [range(fret - config.frets_before_anchor, fret + config.frets_after_anchor + 1)
               for fret in config.anchor_frets]
    expected = sum(len(fret_inlays(0, 0, 1, fret, config.theme.line, config.theme.inlay_radius))
                   for window in windows for fret in window)
    assert len(root.findall('.//*[@data-inlay-fret]')) == expected


def test_staff_and_guitar_background_lines_and_inlays_are_black() -> None:
    config = settings()
    staff = ET.fromstring('<svg>' + ''.join(staff_svg(config, ('M0 0', 'M0 0'))) + '</svg>')
    assert all(node.attrib['stroke'] == '#000000' for node in staff.iter('line'))
    for key in config.overview.keys:
        transposed = transpose_settings(config, key)
        for panel, string in enumerate((5, 4, 3, 2, 1, 0)):
            root = ET.fromstring('<svg>' + ''.join(guitar_svg(transposed, panel, string)) + '</svg>')
            assert all(node.attrib['stroke'] == '#000000' for node in root.iter('line'))
            for mark in root.findall('.//*[@data-inlay-fret]'):
                assert mark.attrib['fill'] == '#000000'
                assert float(mark.attrib['r']) == 4


def test_inlays_only_appear_in_six_guitar_panels_not_blocks() -> None:
    config = settings()
    blocks = ET.fromstring('<svg>' + ''.join(blocks_svg(config)) + '</svg>')
    assert blocks.findall('.//*[@data-inlay-fret]') == []
    for panel, string in enumerate((5, 4, 3, 2, 1, 0)):
        diagram = ET.fromstring('<svg>' + ''.join(guitar_svg(config, panel, string)) + '</svg>')
        assert diagram.findall('.//*[@data-inlay-fret]')


def test_blocks_match_requested_notes_and_intervals() -> None:
    config = settings()
    positions = block_positions(config)
    assert [note.name() for _, _, note in positions] == [
        "D4", "E4", "F4", "G4", "A3", "B3", "C4", "D4",
    ]
    assert [note.degree + 1 for _, _, note in positions] == [2, 3, 4, 5, 6, 7, 1, 2]
    for row in (0, 1):
        frets = [fret for r, fret, _ in positions if r == row]
        assert frets == [7, 9, 10, 12]
        assert [b - a for a, b in zip(frets, frets[1:])] == [2, 1, 2]


def test_block_coordinates_preserve_fret_distances() -> None:
    root = ET.fromstring('<svg>' + ''.join(blocks_svg(settings())) + '</svg>')
    for string in (3, 4):
        groups = [node for node in root.findall('.//*[@data-block]')
                  if node.attrib["data-string"] == str(string)]
        assert len(groups) == 4
        circles = [node.find('{*}circle') for node in groups]
        assert all(circle is not None for circle in circles)
        xs = [float(circle.attrib["cx"]) for circle in circles if circle is not None]
        gaps = [b - a for a, b in zip(xs, xs[1:])]
        assert gaps[1] > 0
        assert gaps[0] == gaps[2] == gaps[1] * 2


def test_compact_staff_uses_shared_middle_c_coordinate() -> None:
    for note in scale_notes(41, 84):
        assert staff_y(note, "treble") == staff_y(note, "bass")
    assert staff_y(Note.from_midi(60), "treble") == 192
    assert ledger_lines(192, 178, 14) == ledger_lines(192, 262, 14) == (192,)


def test_compact_layout_has_black_white_keys_with_colored_dots() -> None:
    config = settings()
    root = ET.fromstring(render_svg(config, ("M0 0", "M0 0")))
    assert root.attrib["viewBox"] == "0 0 1600 576"
    for node in root.findall('.//{*}g[@data-degree]'):
        labels = node.findall('{*}text')
        assert len(labels) == 1
        note = Note.from_midi(int(node.attrib["data-midi"]))
        assert labels[0].text == note.letter
        assert labels[0].attrib["fill"] == "#FFFFFF"
        assert labels[0].attrib["font-weight"] == "400"
        if node.attrib.get("id", "").startswith("key-"):
            keys = node.findall('{*}rect')
            assert len(keys) == 1
            assert keys[0].attrib["fill"] == config.theme.white_key
            assert "opacity" not in keys[0].attrib
            circle = node.find('{*}circle')
            assert circle is not None
            assert circle.attrib['fill'] == config.colors[note.degree]
    texts = [node.text or "" for node in root.findall('.//{*}text')]
    assert "C major" not in texts
    assert not any("说明" in value or "主音在" in value or "统一级数" in value for value in texts)


def test_guitar_panels_have_two_above_four_below_and_no_titles() -> None:
    config = settings()
    origins: list[tuple[float, float]] = []
    for panel, string in enumerate((5, 4, 3, 2, 1, 0)):
        diagram = ET.fromstring('<svg>' + ''.join(guitar_svg(config, panel, string)) + '</svg>')
        card = diagram.find('rect')
        assert card is not None
        origins.append((float(card.attrib['x']), float(card.attrib['y'])))
        assert all((label.text or '').isdigit() for label in diagram.findall('text'))
        for circle in diagram.findall('.//circle'):
            x, y = float(circle.attrib['cx']), float(circle.attrib['cy'])
            radius = float(circle.attrib['r'])
            left, top = origins[-1]
            assert left <= x - radius < x + radius <= left + 380
            assert top <= y - radius < y + radius <= top + 208
    assert origins == [(808, 72), (1204, 72), (16, 352),
                       (412, 352), (808, 352), (1204, 352)]


@pytest.mark.parametrize("accidental,label,weight", [
    (-1, "D♭", "400"), (0, "D", "400"), (1, "D♯", "400"),
])
def test_user_accidental_typography(accidental: int, label: str, weight: str) -> None:
    node = ET.fromstring(pitch_label(0, 0, "D", accidental, 14))
    assert node.text == label
    assert node.attrib["font-weight"] == weight


@pytest.mark.parametrize("block", [
    {"upper_string": 2, "first_fret": 3},  # G/B exception must not render aligned.
    {"upper_string": 6, "first_fret": 7},
    {"upper_string": True, "first_fret": 7},
    {"upper_string": 3, "first_fret": 8},
    {"upper_string": 3, "first_fret": 20},
])
def test_reject_invalid_block_placement(block: dict[str, int]) -> None:
    with Path("config/c-major-atlas.toml").open("rb") as stream:
        raw = tomllib.load(stream)
    raw["blocks"] = block
    with pytest.raises(ValueError):
        parse_settings(raw, Path("config"))


@pytest.mark.parametrize("field,value", [
    ("first_midi", True), ("first_midi", 42), ("last_midi", 85),
    ("colors", ["#ffffff"] * 6), ("colors", ["invalid"] * 7),
    ("anchor_frets", [0] * 6),
    ("frets_before_anchor", 5), ("tuning", [40]),
])
def test_reject_bad_config(field: str, value: object) -> None:
    with Path("config/c-major-atlas.toml").open("rb") as stream:
        raw = tomllib.load(stream)
    raw[field] = value
    with pytest.raises(ValueError):
        parse_settings(raw, Path("config"))


def test_cli_protects_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "atlas.svg"
    command = [sys.executable, "scripts/render_key_atlas.py", "--output", str(output)]
    first = subprocess.run(command, capture_output=True, text=True, check=False)
    assert first.returncode == 0, first.stderr
    original = output.read_bytes()
    second = subprocess.run(command, capture_output=True, text=True, check=False)
    assert second.returncode == 2
    assert output.read_bytes() == original
    third = subprocess.run(command + ["--force"], capture_output=True, text=True, check=False)
    assert third.returncode == 0, third.stderr
    assert output.read_bytes() == original


@pytest.mark.parametrize("name,spellings", [
    ("C", "C D E F G A B"),
    ("Db", "D♭ E♭ F G♭ A♭ B♭ C"),
    ("D", "D E F♯ G A B C♯"),
    ("Eb", "E♭ F G A♭ B♭ C D"),
    ("E", "E F♯ G♯ A B C♯ D♯"),
    ("F", "F G A B♭ C D E"),
    ("Gb", "G♭ A♭ B♭ C♭ D♭ E♭ F"),
    ("G", "G A B C D E F♯"),
    ("Ab", "A♭ B♭ C D♭ E♭ F G"),
    ("A", "A B C♯ D E F♯ G♯"),
    ("Bb", "B♭ C D E♭ F G A"),
    ("B", "B C♯ D♯ E F♯ G♯ A♯"),
])
def test_twelve_major_spellings(name: str, spellings: str) -> None:
    key = MajorKey.from_name(name)
    actual: list[str] = []
    for pc in key.pitch_classes:
        note = key.note(60 + pc)
        assert note is not None
        actual.append(note.name()[:-1])
    assert ' '.join(actual) == spellings
    assert [(b - a) % 12 for a, b in zip(key.pitch_classes, key.pitch_classes[1:] + key.pitch_classes[:1])] == [2, 2, 1, 2, 2, 2, 1]


def test_g_flat_c_flat_uses_correct_written_octave_and_staff_line() -> None:
    note = MajorKey.from_name("Gb").note(59)
    assert note is not None and note.name() == "C♭4"
    assert note.degree == 3 and note.accidental == -1
    assert staff_y(note, 'bass') == 192  # C4 ledger, not B3 space.


@given(st.integers(0, 127))
def test_written_pitch_roundtrips_to_midi(midi: int) -> None:
    for key in settings().overview.keys:
        note = key.note(midi)
        if note is not None:
            natural = (0, 2, 4, 5, 7, 9, 11)['CDEFGAB'.index(note.letter)]
            assert (note.octave + 1) * 12 + natural + note.accidental == midi
            assert key.pitch_classes[note.degree] == midi % 12


def test_every_key_transposes_all_views_and_block_intervals() -> None:
    base = settings()
    for key in base.overview.keys:
        config = transpose_settings(base, key)
        for row, fret in enumerate(config.anchor_frets):
            assert (config.tuning[row] + fret) % 12 == key.pitch_classes[0]
            assert 0 <= fret - config.frets_before_anchor <= fret + config.frets_after_anchor <= 24
        assert [note.degree for _, _, note in block_positions(config)] == [1, 2, 3, 4, 5, 6, 0, 1]
        root = ET.fromstring(render_svg(config, ('M0 0', 'M0 0')))
        expected = {note.midi for note in key.notes(config.first_midi, config.last_midi)}
        keyboard = {int(node.attrib['data-midi']) for node in root.findall('.//{*}g[@data-black]')
                    if 'data-degree' in node.attrib}
        staff = {int(node.attrib['data-midi']) for node in root.findall('.//{*}g')
                 if node.attrib.get('id', '').startswith('note-')}
        assert keyboard == staff == expected
        assert len(root.findall('.//*[@data-anchor="true"]')) == 6
        for node in root.findall('.//{*}g[@data-degree]'):
            note = key.note(int(node.attrib['data-midi']))
            assert note is not None
            assert node.attrib['data-color'] == config.colors[note.degree]
            label = node.find('{*}text')
            assert label is not None
            assert label.text == note.letter + {-1: '♭', 0: '', 1: '♯'}[note.accidental]
            assert label.attrib['font-weight'] == '400'
        for node in root.findall('.//{*}g[@data-black]'):
            key_rect = node.find('{*}rect')
            assert key_rect is not None
            assert key_rect.attrib['fill'] == (config.theme.black_key if node.attrib['data-black'] == 'true'
                                               else config.theme.white_key)


def test_overview_is_four_by_three_with_unique_ids_and_g_flat() -> None:
    root = ET.fromstring(render_overview(settings(), ('M0 0', 'M0 0')))
    keys = root.findall('.//{*}g[@data-key]')
    assert [node.attrib['data-key'] for node in keys] == [
        'C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B',
    ]
    assert root.attrib['viewBox'] == '0 0 6480 1792'
    ids = [node.attrib['id'] for node in root.iter() if 'id' in node.attrib]
    assert len(ids) == len(set(ids))
    assert len(root.findall('.//*[@data-anchor="true"]')) == 72
    assert root.findall('.//*[@data-block]') == []
    assert len({node.attrib['transform'].split()[0] for node in keys}) == 4


@pytest.mark.parametrize('theme', ['light', 'dark'])
@pytest.mark.parametrize('mode', ['--all-keys', '--stacked'])
def test_overview_cli(tmp_path: Path, mode: str, theme: str) -> None:
    output = tmp_path / 'all.svg'
    result = subprocess.run([sys.executable, 'scripts/render_key_atlas.py', mode,
                             '--theme', theme, '--output', str(output)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert len(ET.parse(output).getroot().findall('.//{*}g[@data-key]')) == 12
    background = ET.parse(output).getroot().find('{*}rect')
    assert background is not None and background.attrib['fill'] == settings(theme).theme.paper


@pytest.mark.parametrize('theme', ['light', 'dark'])
@pytest.mark.parametrize('first,last', [(41, 84), (36, 84), (59, 60)])
def test_staff_notes_alternate_without_overlap_or_clipping(theme: str, first: int, last: int) -> None:
    base = replace(settings(theme), first_midi=first, last_midi=last)
    for key in base.overview.keys:
        config = transpose_settings(base, key)
        root = ET.fromstring('<svg>' + ''.join(staff_svg(config, ('M0 0', 'M0 0'))) + '</svg>')
        groups = root.findall('.//g[@data-midi]')
        assert len(groups) == len(key.notes(first, last))
        dots: list[tuple[float, float, float]] = []
        for group in groups:
            circle = group.find('circle')
            assert circle is not None
            x, y, radius = (float(circle.attrib[attr]) for attr in ('cx', 'cy', 'r'))
            note = key.note(int(group.attrib['data-midi']))
            assert note is not None
            assert x == 214 + note.staff_step() % 2 * 24
            assert y == 16 + (42 - note.staff_step()) * 11
            assert 0 <= y - radius < y + radius < 352
            assert 32 < x - radius < x + radius < 278
            dots.append((x, y, radius))
        for (x1, y1, r1), (x2, y2, r2) in combinations(dots, 2):
            assert hypot(x1 - x2, y1 - y2) > r1 + r2
        # No later ledger line may overwrite an already painted note dot.
        painted: list[tuple[float, float, float]] = []
        for element in root:
            if element.tag == 'g' and 'data-midi' in element.attrib:
                dot = element.find('circle')
                assert dot is not None
                painted.append(tuple(float(dot.attrib[attr]) for attr in ('cx', 'cy', 'r')))
            if element.tag == 'line' and element.attrib['y1'] == element.attrib['y2']:
                x1, x2, y = (float(element.attrib[attr]) for attr in ('x1', 'x2', 'y1'))
                assert all(hypot(x - min(max(x, x1), x2), cy - y) > radius
                           for x, cy, radius in painted)


@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_theme_lines_labels_and_physical_keys(theme: str) -> None:
    base = settings(theme)
    expected_line = '#000000' if theme == 'light' else '#FFFFFF'
    assert base.theme.line == expected_line
    assert base.theme.paper == base.theme.panel == ('#FFFFFF' if theme == 'light' else '#000000')
    assert len(set(base.colors)) == 4
    assert base.colors[1] == base.colors[2]
    assert base.colors[3] == base.colors[4]
    assert base.colors[5] == base.colors[6]
    for key in base.overview.keys:
        config = transpose_settings(base, key)
        root = ET.fromstring(render_svg(config, ('M0 0', 'M0 0')))
        assert all(node.attrib['stroke'] == expected_line for node in root.findall('.//{*}line'))
        for node in root.findall('.//{*}g[@data-degree]'):
            note = key.note(int(node.attrib['data-midi']))
            assert note is not None
            assert node.attrib['data-color'] == config.colors[note.degree]
            label = node.find('{*}text')
            assert label is not None
            assert label.text == note.letter + {-1: '♭', 0: '', 1: '♯'}[note.accidental]
        keys = root.findall('.//{*}g[@data-black]')
        assert len(keys) == config.last_midi - config.first_midi + 1
        for node in keys:
            body = node.find('{*}rect')
            assert body is not None
            assert body.attrib['fill'] == (config.theme.black_key if node.attrib['data-black'] == 'true'
                                            else '#FFFFFF')


def test_dark_palette_is_brighter_without_changing_hue_groups() -> None:
    from colorsys import rgb_to_hsv

    for light, dark in zip(settings().colors, settings('dark').colors, strict=True):
        l_hue, _, l_value = rgb_to_hsv(*(int(light[i:i + 2], 16) / 255 for i in (1, 3, 5)))
        d_hue, _, d_value = rgb_to_hsv(*(int(dark[i:i + 2], 16) / 255 for i in (1, 3, 5)))
        assert abs(l_hue - d_hue) < 0.025
        assert d_value > l_value


def test_reject_unknown_theme() -> None:
    with pytest.raises(ValueError, match='Theme must be light or dark'):
        settings('sepia')


def test_side_dots_are_below_strings_in_all_keys() -> None:
    base = settings()
    for key in base.overview.keys:
        config = transpose_settings(base, key)
        for panel, string in enumerate((5, 4, 3, 2, 1, 0)):
            root = ET.fromstring('<svg>' + ''.join(guitar_svg(config, panel, string)) + '</svg>')
            lines = root.findall('line')
            fret_lines = [line for line in lines if line.attrib['x1'] == line.attrib['x2']]
            assert len(fret_lines) == 8  # Seven fret columns, including both edges.
            fret_labels = [node.text for node in root.findall('text')][:7]
            anchor = config.anchor_frets[string]
            assert fret_labels == [str(fret) for fret in range(anchor - 2, anchor + 5)]
            bottom = max(float(line.attrib['y2']) for line in lines)
            for mark in root.findall('.//*[@data-inlay-fret]'):
                assert float(mark.attrib['cy']) - float(mark.attrib['r']) > bottom


def test_mobile_has_same_twelve_tiles_stacked_without_footer() -> None:
    base = settings()
    grid = ET.fromstring(render_overview(base, ('M0 0', 'M0 0')))
    mobile = ET.fromstring(render_overview(base, ('M0 0', 'M0 0'), stacked=True))
    assert mobile.attrib['viewBox'] == '0 0 1632 7120'
    grid_tiles = grid.findall('.//{*}g[@data-key]')
    mobile_tiles = mobile.findall('.//{*}g[@data-key]')
    assert len(grid_tiles) == len(mobile_tiles) == 12
    for index, (grid_tile, mobile_tile) in enumerate(zip(grid_tiles, mobile_tiles)):
        assert mobile_tile.attrib['transform'] == f'translate(16 {16 + index * 592})'
        assert grid_tile.attrib['data-key'] == mobile_tile.attrib['data-key']
        assert [ET.tostring(child) for child in grid_tile] == [
            ET.tostring(child) for child in mobile_tile
        ]
    for root in (grid, mobile):
        for tile in root.findall('.//{*}g[@data-key]'):
            assert tile.findall('{*}text') == []
            assert tile.findall('{*}circle') == []
            content = tile.find('{*}g')
            assert content is not None
            assert 'transform' not in content.attrib
            assert content.findall('.//*[@data-degree]')
        outer_group = root.find('{*}g')
        assert outer_group is not None
        assert outer_group.findall('{*}text') == []
        texts = ' '.join(node.text or '' for node in root.findall('.//{*}text'))
        assert 'MAJOR' not in texts
        assert '说明' not in texts and '小写' not in texts
