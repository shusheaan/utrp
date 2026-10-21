"""Regression checks for the native map-time Chord Lab window rule."""
from pathlib import Path
import re

import pytest


@pytest.mark.parametrize(('title', 'expected'), [
    ('CHORD LAB - shared MIDI input / Chord Lab', True),
    ('GUITAR - raw detection / Chord Lab', True),
    ('Group / Track / Chord Lab', True),
    ('Bitwig Studio - Library', False),
    ('Chord Lab', False),
    ('Track / Surge XT Effects', False),
    ('Track / Chord Lab Extra', False),
    ('Track / Chord Lab / Dialog', False),
])
def test_chord_editor_map_rule(title: str, expected: bool) -> None:
    config = Path(__file__).with_name('sway.conf').read_text()
    rules = [line for line in config.splitlines()
             if line.startswith('for_window ') and 'Chord Lab' in line]
    assert len(rules) == 1
    rule = rules[0]
    assert 'shell="xwayland"' in rule and 'window_type="normal"' in rule
    pattern = re.search(r'title="([^"]+)"', rule)
    assert pattern is not None
    assert bool(re.search(pattern.group(1), title)) is expected
    assert rule.endswith('floating enable, resize set width 920 px height 703 px')
