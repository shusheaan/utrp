"""Ranking invariants, retained archives and evidence labels."""
from dataclasses import replace
from pathlib import Path
import re
import tomllib

import pytest

from scripts.cover_library import entries, index_text, load_entry, validate
from scripts.render_cover import load_style, parse_song, position_midi, midi_note


def test_exact_twelve_by_five_and_index_is_current() -> None:
    root = Path('covers')
    items = entries(root)
    validate(items, 5)
    assert (root/'readme.md').read_text() == index_text(items, root, 5)
    assert len(items) >= 60
    assert sum(bool(i.original) for i in items) == 36


def test_ranking_replacement_keeps_old_assets() -> None:
    root = Path('covers')
    items = entries(root)
    old = next(i for i in items if i.group == 'A' and i.rank == 1)
    alternate = next(i for i in items if i.group == 'A' and not i.rank)
    before = {i.path.with_suffix(s):i.path.with_suffix(s).read_bytes()
              for i in (old,alternate) for s in ('.md','.png','.toml')}
    swapped = tuple(replace(i,rank=0) if i==old else replace(i,rank=1) if i==alternate else i for i in items)
    validate(swapped,5)
    text = index_text(swapped,root,5)
    assert 'Pink + White' in text.split('## 榜外保留')[1]
    assert all(path.read_bytes()==data for path,data in before.items())


def test_missing_duplicate_and_overfull_slots_fail() -> None:
    items = entries(Path('covers'))
    selected = next(i for i in items if i.rank == 1)
    for rank in (0,2,6):
        invalid = tuple(replace(i,rank=rank) if i==selected else i for i in items)
        with pytest.raises(ValueError,match='active ranks'):
            validate(invalid,5,assets=False)


def test_invalid_metadata_is_not_coerced(tmp_path: Path) -> None:
    original = next(Path('covers').glob('*/*.toml')).read_text()
    for rank in ('true','-1','1.5','"1"'):
        path = tmp_path/'invalid.toml'
        path.write_text(re.sub(r'(?m)^rank = \d+$',f'rank = {rank}',original))
        with pytest.raises(ValueError,match='rank'):
            load_entry(path)


def test_markdown_local_links_resolve() -> None:
    for path in Path('covers').rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text()):
            if '://' not in target:
                assert (path.parent/target).is_file(), (path,target)


def test_pending_melodies_are_not_mislabeled_transcriptions() -> None:
    for entry in entries(Path('covers')):
        if entry.melody_status != 'pending':
            continue
        raw = tomllib.loads(entry.path.read_text())
        assert '待核' in raw['status']
        assert '待核' in entry.path.with_suffix('.md').read_text()
        for card in raw['cards']:
            if card['kind'] == 'melody':
                assert card['evidence'] == 'arrangement'
                assert '自编' in card['title']
                assert '不是原' in card['footer']


def test_beat_it_half_step_tuning_and_octave_transfer() -> None:
    path = Path('covers/G-flat-major_E-flat-minor/michael-jackson--beat-it.toml')
    config = load_style(Path('config/cover-atlas.toml'))
    song = parse_song(tomllib.loads(path.read_text()),config)
    card = next(c for c in song.cards if c.title.startswith('吉他 riff'))
    down_half = tuple(n-1 for n in config.tuning)
    source_positions = ('E0','E3','A2','D5','D2','D2')
    assert tuple(midi_note(n) for n in card.notes) == tuple(
        position_midi(p,down_half)+12 for p in source_positions)


def test_generated_exercise_chromatic_octaves_are_spelled_correctly() -> None:
    config = load_style(Path('config/cover-atlas.toml'))
    for entry in entries(Path('covers')):
        song = parse_song(tomllib.loads(entry.path.read_text()),config)
        for card in song.cards:
            if '上行拆分' in card.title:
                midi = [midi_note(n) for n in card.notes]
                assert midi == sorted(midi)
            if '下行拆分' in card.title:
                midi = [midi_note(n) for n in card.notes]
                assert midi == sorted(midi,reverse=True)
