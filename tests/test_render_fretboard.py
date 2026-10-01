"""Musical, boundary and SVG checks for the small score-matrix renderer."""

from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import tomllib
from xml.etree import ElementTree

from hypothesis import given, strategies as st
import pytest

from scripts.render_fretboard import (
    Position, Settings, coordinates, parse_settings, pitch_class, render_svg, scale_positions,
)


def example() -> Settings:
    with Path("sheets/NLND_TABS/drown-matrices.toml").open("rb") as stream:
        return parse_settings(tomllib.load(stream))


@given(st.integers(0, 5), st.integers(0, 24))
def test_octave_equivalence(row: int, fret: int) -> None:
    tuning = (64, 59, 55, 50, 45, 40)
    assert pitch_class(Position(row, fret), tuning) == pitch_class(Position(row, fret+12), tuning)


@given(st.sets(st.integers(0, 11), min_size=1), st.integers(0, 20))
def test_scale_generation_is_complete(pitches: set[int], first: int) -> None:
    tuning = (64, 59, 55, 50, 45, 40)
    result = scale_positions(tuning, tuple(pitches), first, first+4)
    expected = {Position(row, fret) for row in range(6) for fret in range(first, first+5)
                if (tuning[row]+fret) % 12 in pitches}
    assert set(result) == expected
    assert len(result) == len(expected)


def test_verified_score_landmarks() -> None:
    settings = example()
    assert pitch_class(Position(2, 11), settings.tuning) == 6  # G11 = F#
    assert pitch_class(Position(4, 9), settings.tuning) == 6   # A9 = F#
    fourths = settings.diagrams[2]
    for p in fourths.paths[0]:
        upper = Position(p.string-1, p.fret)
        assert (pitch_class(upper, settings.tuning)-pitch_class(p, settings.tuning)) % 12 == 5
    arpeggio = settings.diagrams[4]
    assert {pitch_class(p, settings.tuning) for p in arpeggio.anchors} == {9, 0, 4, 6}


def test_rendered_svg_is_well_formed_and_positions_are_in_bounds() -> None:
    settings = example()
    for diagram in settings.diagrams:
        svg = render_svg(diagram, settings)
        root = ElementTree.fromstring(svg)
        assert root.attrib["viewBox"] == "0 0 1440 620"
        for p in diagram.anchors:
            x, y = coordinates(p, diagram)
            assert 140 < x < 1360
            assert 205 <= y <= 450
        assert len(root.findall('.//{*}circle[@r="23"]')) == len(diagram.anchors)
        assert root.find('{*}title') is not None


def test_xml_text_is_escaped() -> None:
    settings = example()
    diagram = replace(settings.diagrams[0], title='<script>alert("x")</script> & text')
    root = ElementTree.fromstring(render_svg(diagram, settings))
    assert root.find('{*}script') is None
    title = root.find('{*}title')
    assert title is not None and title.text == diagram.title


def test_adjacent_string_route_curves_outside_markers() -> None:
    settings = example()
    anchors = (Position(0, 12), Position(1, 12))
    diagram = replace(settings.diagrams[0], anchors=anchors, paths=(anchors,))
    root = ElementTree.fromstring(render_svg(diagram, settings))
    arrows = root.findall('.//{*}path[@marker-end]')
    assert len(arrows) == 1
    assert 'Q' in arrows[0].attrib['d']


@pytest.mark.parametrize("field,value", [
    ("slug", "../outside"), ("first", True), ("last", 36), ("tonic", 12),
    ("context", [False]), ("auto_scale", "yes"), ("anchors", ["Z9"]),
])
def test_bad_diagram_is_rejected(field: str, value: object) -> None:
    with Path("sheets/NLND_TABS/drown-matrices.toml").open("rb") as stream:
        raw = tomllib.load(stream)
    raw["diagrams"][0][field] = value
    with pytest.raises(ValueError):
        parse_settings(raw)


def test_cli_refuses_overwrite(tmp_path: Path) -> None:
    command = [sys.executable, "scripts/render_fretboard.py",
               "sheets/NLND_TABS/drown-matrices.toml", "--output", str(tmp_path)]
    first = subprocess.run(command, capture_output=True, text=True, check=False)
    assert first.returncode == 0, first.stderr
    assert len(list(tmp_path.glob('*.svg'))) == 5
    second = subprocess.run(command, capture_output=True, text=True, check=False)
    assert second.returncode == 2
    assert 'Output exists' in second.stderr
    third = subprocess.run(command + ['--force'], capture_output=True, text=True, check=False)
    assert third.returncode == 0, third.stderr
