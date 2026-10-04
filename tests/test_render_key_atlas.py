"""Musical alignment and shared-color checks for the C-major atlas."""

from pathlib import Path
import subprocess
import sys
import tomllib
from xml.etree import ElementTree as ET

from hypothesis import given, strategies as st
import pytest

from scripts.render_key_atlas import (
    MajorKey, Note, Settings, block_positions, blocks_svg, fret_inlays, guitar_positions, guitar_svg,
    ledger_lines, parse_settings, render_svg,
    pitch_label, render_overview, scale_notes, staff_y, transpose_settings,
)


def settings() -> Settings:
    path = Path("config/c-major-atlas.toml")
    with path.open("rb") as stream:
        return parse_settings(tomllib.load(stream), path.parent)


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


@pytest.mark.parametrize("fret,count", [
    (0, 0), (1, 0), (2, 0), (3, 1), (4, 0), (5, 1), (6, 0),
    (7, 1), (8, 0), (9, 1), (10, 0), (11, 0), (12, 2),
    (13, 0), (15, 0), (17, 0), (19, 0), (21, 0), (24, 0),
])
def test_standard_fret_inlays(fret: int, count: int) -> None:
    marks = [ET.fromstring(part) for part in fret_inlays(100, 200, 30, fret, "#70808B")]
    assert len(marks) == count
    assert all(mark.attrib["data-inlay-fret"] == str(fret) for mark in marks)
    assert all(float(mark.attrib["cy"]) == 200 for mark in marks)
    if count == 2:
        assert [float(mark.attrib["cx"]) for mark in marks] == [70, 130]


def test_inlays_render_in_all_visible_fret_windows() -> None:
    config = settings()
    root = ET.fromstring(render_svg(config, ("M0 0", "M0 0")))
    windows = [range(fret - config.frets_before_anchor, fret + config.frets_after_anchor + 1)
               for fret in config.anchor_frets]
    expected = sum(len(fret_inlays(0, 0, 1, fret, "#70808B"))
                   for window in windows for fret in window)
    assert len(root.findall('.//*[@data-inlay-fret]')) == expected


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
    assert root.attrib["viewBox"] == "0 0 1600 696"
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
            assert keys[0].attrib["fill"] == config.theme.panel
            assert "opacity" not in keys[0].attrib
            circle = node.find('{*}circle')
            assert circle is not None
            assert circle.attrib['fill'] == config.colors[note.degree]
    texts = [node.text or "" for node in root.findall('.//{*}text')]
    assert "C major" not in texts
    assert not any("说明" in value or "主音在" in value or "统一级数" in value for value in texts)


def test_guitar_panels_have_three_columns_two_rows_and_no_titles() -> None:
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
            assert left <= x - radius < x + radius <= left + 512
            assert top <= y - radius < y + radius <= top + 208
    assert origins == [(16, 300), (544, 300), (1072, 300),
                       (16, 524), (544, 524), (1072, 524)]


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
                                               else config.theme.panel)


def test_overview_is_four_by_three_with_unique_ids_and_g_flat() -> None:
    root = ET.fromstring(render_overview(settings(), ('M0 0', 'M0 0')))
    keys = root.findall('.//{*}g[@data-key]')
    assert [node.attrib['data-key'] for node in keys] == [
        'C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B',
    ]
    assert root.attrib['viewBox'] == '0 0 6480 2284'
    ids = [node.attrib['id'] for node in root.iter() if 'id' in node.attrib]
    assert len(ids) == len(set(ids))
    assert len(root.findall('.//*[@data-anchor="true"]')) == 72
    assert root.findall('.//*[@data-block]') == []
    assert len({node.attrib['transform'].split()[0] for node in keys}) == 4


@pytest.mark.parametrize('mode', ['--all-keys', '--stacked'])
def test_overview_cli(tmp_path: Path, mode: str) -> None:
    output = tmp_path / 'all.svg'
    result = subprocess.run([sys.executable, 'scripts/render_key_atlas.py', mode,
                             '--output', str(output)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert len(ET.parse(output).getroot().findall('.//{*}g[@data-key]')) == 12


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
    assert mobile.attrib['viewBox'] == '0 0 1632 9088'
    grid_tiles = grid.findall('.//{*}g[@data-key]')
    mobile_tiles = mobile.findall('.//{*}g[@data-key]')
    assert len(grid_tiles) == len(mobile_tiles) == 12
    for index, (grid_tile, mobile_tile) in enumerate(zip(grid_tiles, mobile_tiles)):
        assert mobile_tile.attrib['transform'] == f'translate(16 {16 + index * 756})'
        assert grid_tile.attrib['data-key'] == mobile_tile.attrib['data-key']
        assert [ET.tostring(child) for child in grid_tile] == [
            ET.tostring(child) for child in mobile_tile
        ]
    for root in (grid, mobile):
        outer_group = root.find('{*}g')
        assert outer_group is not None
        assert outer_group.findall('{*}text') == []
        texts = ' '.join(node.text or '' for node in root.findall('.//{*}text'))
        assert 'MAJOR' not in texts
        assert '说明' not in texts and '小写' not in texts
