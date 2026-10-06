"""Check source-note arithmetic, chart boundaries and the three-file cover layout."""

from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import tomllib
from xml.etree import ElementTree as ET

from hypothesis import given, strategies as st
import pytest

from scripts.render_cover import (
    Card, Song, Style, atlas, atlas_settings, load_style, melody_staff, midi_note,
    note_color, parse_card, parse_song, parse_style, pitch_class, position_midi, render_svg,
)


def style() -> Style:
    return load_style(Path("config/cover-atlas.toml"))


def clefs() -> tuple[str, str]:
    return atlas.load_clefs(style().atlas.music_font)


def song(path: Path) -> Song:
    with path.open("rb") as stream:
        return parse_song(tomllib.load(stream), style())


def chord_data() -> dict[str, object]:
    return {
        "kind": "chord", "title": "Cmaj7", "subtitle": "source-grounded test",
        "scale": ["C", "D", "E", "F#", "G", "A", "B"],
        "notes": ["C", "E", "G", "B"], "anchor_frets": [8, 13, 5, 10, 3, 8],
        "footer": "Practice collection, not a voicing",
    }


def melody_data() -> dict[str, object]:
    return {
        **chord_data(), "kind": "melody", "notes": ["G4", "A4"],
        "positions": ["B8", "e5"], "anchor_frets": [3, 8, 12, 5, 10, 3],
    }


@pytest.mark.parametrize("name,midi", [
    ("C4", 60), ("F#4", 66), ("G#4", 68), ("C#5", 73),
    ("Cb4", 59), ("B#3", 60), ("C-1", 0), ("G9", 127),
])
def test_note_spelling(name: str, midi: int) -> None:
    assert midi_note(name) == midi


@pytest.mark.parametrize("name", ["H4", "C", "G#9", "Cb-1", "C10", "c4"])
def test_invalid_note(name: str) -> None:
    with pytest.raises(ValueError):
        midi_note(name)


@given(st.sampled_from(tuple("CDEFGAB")), st.sampled_from(("", "#", "b")),
       st.integers(0, 7))
def test_octave_and_pitch_class_invariants(letter: str, accidental: str, octave: int) -> None:
    name = letter + accidental
    midi = midi_note(f"{name}{octave}")
    assert midi_note(f"{name}{octave + 1}") == midi + 12
    assert midi % 12 == pitch_class(name)


@given(st.sampled_from(tuple("eBGDAE")), st.integers(0, 12))
def test_guitar_octave_invariant(string: str, fret: int) -> None:
    tuning = style().tuning
    assert position_midi(f"{string}{fret + 12}", tuning) == position_midi(f"{string}{fret}", tuning) + 12


def test_unity_tab_is_not_misread_as_e4() -> None:
    config = style()
    assert position_midi("B9", config.tuning) == midi_note("G#4")
    assert position_midi("B14", config.tuning) == midi_note("C#5")
    assert position_midi("B7", config.tuning) == midi_note("F#4")


@pytest.mark.parametrize("field,value", [
    ("scale", ["C", "D", "E", "F", "G", "A", "A"]),
    ("scale", ["C", "D", "E", "F", "G", "A"]),
    ("notes", ["C", "E", "G", "G"]),
    ("notes", ["C", "E", "G", "Bb"]),
    ("notes", ["C", "B", "E", "G"]),
    ("kind", "automatic"), ("anchor_frets", [True, 13, 5, 10, 3, 8]),
    ("anchor_frets", [-1, 13, 5, 10, 3, 8]), ("anchor_frets", [8, 13]),
    ("anchor_frets", [8, 13, 5, 10, 3, 24]), ("anchor_frets", [8, 13, 5, 10, 3, 7]),
    ("positions", ["B8"]),
])
def test_invalid_chord(field: str, value: object) -> None:
    raw = chord_data()
    raw[field] = value
    with pytest.raises(ValueError):
        parse_card(raw, style())


@pytest.mark.parametrize("field,value", [
    ("notes", ["G4"]), ("positions", ["B8"]),
    ("positions", ["e25", "e5"]), ("positions", ["B7", "e5"]),
    ("notes", ["G3", "A3"]), ("notes", ["G#4", "A4"]),
    ("positions", ["Z8", "e5"]),
])
def test_invalid_melody(field: str, value: object) -> None:
    raw = melody_data()
    raw[field] = value
    with pytest.raises(ValueError):
        parse_card(raw, style())


def test_chord_color_is_relative_to_chord_not_song() -> None:
    config = style()
    card = parse_card(chord_data(), config)
    assert note_color(0, card, config) == config.root
    assert note_color(4, card, config) == config.third
    assert note_color(7, card, config) == config.fifth
    assert note_color(11, card, config) == config.seventh


@pytest.mark.parametrize("path", sorted(Path("covers").rglob("*.toml")))
def test_six_cards_and_exact_melody_positions(path: Path) -> None:
    config, loaded = style(), song(path)
    assert 6 <= len(loaded.cards) <= 8
    for card in loaded.cards:
        if card.kind == "melody":
            assert tuple(position_midi(pos, config.tuning) for pos in card.positions) == tuple(
                midi_note(note) for note in card.notes)
    root = ET.fromstring(render_svg(loaded, config, clefs()))
    namespace = {"s": "http://www.w3.org/2000/svg"}
    cards = [node for node in root.findall(".//s:g[@id]", namespace)
             if node.attrib["id"].startswith("card-")]
    assert len(cards) == len(loaded.cards)
    assert root.attrib["height"] == str(420 + 1030 * len(loaded.cards))
    for suffix in (".md", ".png", ".toml"):
        assert path.with_suffix(suffix).is_file()
    assert path.with_suffix(".png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_catalog_keeps_all_36_candidates() -> None:
    from scripts.cover_library import entries, validate
    items = entries(Path("covers"))
    validate(items, 5)
    assert sum(bool(item.original) for item in items) == 36
    assert sum(item.rank > 0 for item in items) == 60
    assert {item.song for item in items if not item.rank} == {"Monks", "Sierra Leone"}


def test_card_count_boundary() -> None:
    path = next(Path("covers").rglob("*.toml"))
    with path.open("rb") as stream:
        raw = tomllib.load(stream)
    for count in (0, 5, 9):
        invalid = deepcopy(raw)
        invalid["cards"] = [chord_data() for _ in range(count)]
        with pytest.raises(ValueError, match="six to eight"):
            parse_song(invalid, style())


def test_escape_xml() -> None:
    config = style()
    card = Card("A & B <C>", "<not markup>", "chord", ("C", "D", "E", "F#", "G", "A", "B"),
                ("C", "E", "G", "B"), (), (8, 13, 5, 10, 3, 8), "<footer>")
    loaded = Song("<song>", "a & b", "pending", "A → B", "C → D", "practice", (card,) * 6)
    xml = render_svg(loaded, config, clefs())
    ET.fromstring(xml)
    assert "&lt;song&gt;" in xml
    assert "A &amp; B &lt;C&gt;" in xml


def test_cli_preserves_existing_output(tmp_path: Path) -> None:
    config = tmp_path / "test.toml"
    config.write_bytes(next(Path("covers").rglob("*.toml")).read_bytes())
    output = config.with_suffix(".png")
    output.write_bytes(b"existing user file")
    command = [sys.executable, "scripts/render_cover.py", str(config)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert "--force" in result.stderr
    assert output.read_bytes() == b"existing user file"
    result = subprocess.run([*command, "--force"], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.parametrize('path', sorted(Path('covers').rglob('*.toml')))
def test_atlas_tiles_have_six_seven_fret_windows_and_unique_ids(path: Path) -> None:
    config, loaded = style(), song(path)
    root = ET.fromstring(render_svg(loaded, config, clefs()))
    ids = [node.attrib['id'] for node in root.iter() if 'id' in node.attrib]
    assert len(ids) == len(set(ids))
    ns = {'s': 'http://www.w3.org/2000/svg'}
    for index, card in enumerate(loaded.cards, 1):
        settings = atlas_settings(card, config)
        assert settings.frets_before_anchor + settings.frets_after_anchor + 1 == 7
        group = root.find(f".//s:g[@id='card-{index}']", ns)
        assert group is not None
        notes = group.findall('.//s:g[@data-panel]', ns)
        assert {int(node.attrib['data-panel']) for node in notes} == set(range(6))
        for panel, anchor_string in enumerate((5, 4, 3, 2, 1, 0)):
            first = settings.anchor_frets[anchor_string] - 2
            frets = {int(node.attrib['data-fret']) for node in notes
                     if int(node.attrib['data-panel']) == panel}
            assert frets <= set(range(first, first + 7))
            panel_svg = ET.fromstring('<svg>' + ''.join(
                atlas.guitar_svg(settings, panel, anchor_string)) + '</svg>')
            label_y = str((72 if panel < 2 else 352) + 32 - 19)
            labels = panel_svg.findall(f".//text[@y='{label_y}']")
            assert [int(label.text) for label in labels] == list(range(first, first + 7))
        selected = [node for node in notes if node.attrib['data-anchor'] == 'true']
        assert len(selected) == 6
        assert len({int(node.attrib['data-fret']) for node in selected}) >= 4
        assert group.find(f".//s:path[@id='card{index}-treble-clef']", ns) is not None
        assert group.find(f".//s:path[@id='card{index}-bass-clef']", ns) is not None


def test_inlays_are_below_boards_and_twelfth_fret_is_horizontal_pair() -> None:
    config = style()
    card = parse_card(chord_data(), config)
    settings = atlas_settings(card, config)
    for panel, anchor_string in enumerate((5, 4, 3, 2, 1, 0)):
        root = ET.fromstring('<svg>' + ''.join(atlas.guitar_svg(settings, panel, anchor_string)) + '</svg>')
        dots = root.findall('.//circle[@data-inlay-fret]')
        bottom = (72 if panel < 2 else 352) + 32 + 150
        assert all(float(dot.attrib['cy']) > bottom for dot in dots)
        first = settings.anchor_frets[anchor_string] - 2
        for fret in range(first, first + 7):
            matching = [dot for dot in dots if int(dot.attrib['data-inlay-fret']) == fret]
            assert len(matching) == (2 if fret == 12 else int(fret in (3, 5, 7, 9, 15, 17, 19, 21)))
            if len(matching) == 2:
                assert matching[0].attrib['cy'] == matching[1].attrib['cy']
                assert matching[0].attrib['cx'] != matching[1].attrib['cx']


def test_melody_staff_retains_order_repeats_and_actual_octaves() -> None:
    config = style()
    loaded = song(Path('covers/A-major_F-sharp-minor/F-sharp-minor-pending--frank-ocean--unity.toml'))
    card = loaded.cards[4]
    root = ET.fromstring('<svg>' + ''.join(melody_staff(card, config, clefs())) + '</svg>')
    notes = root.findall('.//g[@data-melody-index]')
    assert [int(note.attrib['data-midi']) for note in notes] == [68, 73, 68, 73, 66]
    ys = [float(note.find('circle').attrib['cy']) for note in notes]
    assert ys[0] == ys[2] and ys[1] == ys[3]
    assert ys[1] < ys[0] < ys[4]


@pytest.mark.parametrize('path', sorted(Path('covers').rglob('*.toml')))
def test_melody_notes_clear_caption_and_pitch_labels(path: Path) -> None:
    config = style()
    for card in song(path).cards:
        if card.kind != 'melody':
            continue
        root = ET.fromstring('<svg>' + ''.join(melody_staff(card, config, clefs())) + '</svg>')
        for node in root.findall('.//g[@data-melody-index]'):
            circle = node.find('circle')
            assert circle is not None
            y, radius = float(circle.attrib['cy']), float(circle.attrib['r'])
            assert y - radius > 809
            assert y + radius < 904


def test_six_and_eight_fret_styles_are_rejected() -> None:
    from dataclasses import replace
    with Path('config/cover-atlas.toml').open('rb') as stream:
        raw = tomllib.load(stream)
    for after in (3, 5):
        with pytest.raises(ValueError, match='exactly seven'):
            parse_style(raw, replace(style().atlas, frets_after_anchor=after))


def test_different_position_same_pitch_is_accepted() -> None:
    raw = melody_data()
    raw['positions'] = ['e3', 'e5']
    parsed = parse_card(raw, style())
    assert parsed.positions == ('e3', 'e5')
