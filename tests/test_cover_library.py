"""Ranking invariants, retained archives and evidence labels."""
from dataclasses import replace
from copy import deepcopy
from pathlib import Path
import re
import subprocess
import sys
import tomllib

import pytest

from scripts.cover_library import (
    entries, index_text, load_entry, validate, validate_chord_label,
    validate_content, validate_evidence, validate_rendered,
)
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


def test_zebra_uses_minor_iii_and_includes_bbm() -> None:
    path = Path('covers/A-flat-major_F-minor/beach-house--zebra.toml')
    raw = tomllib.loads(path.read_text())
    chords = {c['title'].split(' · ')[0]: c['notes']
              for c in raw['cards'] if c['kind'] == 'chord'}
    assert 'C' not in chords
    assert chords['Cm'] == ['C', 'Eb', 'G']
    assert chords['Bbm'] == ['Bb', 'Db', 'F']
    assert 'Ab → Bbm → Db → Ab' in raw['progression']


def test_chord_symbol_cannot_disagree_with_valid_chord_tones() -> None:
    config = load_style(Path('config/cover-atlas.toml'))
    path = Path('covers/A-flat-major_F-minor/beach-house--zebra.toml')
    song = parse_song(tomllib.loads(path.read_text()), config)
    minor = next(c for c in song.cards if c.title.startswith('Cm ·'))
    validate_chord_label(minor)
    with pytest.raises(ValueError, match='disagrees'):
        validate_chord_label(replace(minor, title='C · incorrect major label'))


@pytest.mark.parametrize('case', ('source', 'kind', 'evidence', 'arrangement', 'tone'))
def test_content_evidence_and_selected_chord_tones_are_enforced(case: str) -> None:
    path = Path('covers/A-flat-major_F-minor/beach-house--zebra.toml')
    config = load_style(Path('config/cover-atlas.toml'))
    raw = deepcopy(tomllib.loads(path.read_text()))
    if case == 'source':
        raw['cards'][0]['source'] = 'https://example.com/not-a-listed-source'
    elif case == 'kind':
        raw['cards'][0]['evidence'] = 'reference_excerpt'
    elif case == 'evidence':
        raw['cards'][0]['evidence'] = 'verified_by_magic'
    elif case == 'arrangement':
        raw['cards'][-1]['evidence'] = 'reference_excerpt'
        raw['cards'][-1]['source'] = raw['library']['sources'][0]
    else:
        # Bbm contains F, not G; this is still a valid scale pitch and fret.
        raw['cards'][-1]['notes'][-1] = 'G4'
        raw['cards'][-1]['positions'][-1] = 'B8'
    with pytest.raises(ValueError):
        validate_evidence(raw, parse_song(raw, config))


def test_audit_note_and_png_dimensions_are_checked(tmp_path: Path) -> None:
    original = Path('covers/A-flat-major_F-minor/beach-house--zebra.toml')
    config = load_style(Path('config/cover-atlas.toml'))
    path = tmp_path/original.name
    for suffix in ('.toml', '.md', '.png'):
        path.with_suffix(suffix).write_bytes(original.with_suffix(suffix).read_bytes())
    validate_content(path, config)
    md = path.with_suffix('.md')
    saved = md.read_text()
    md.write_text(saved.replace('Verse 开头:', 'incorrect:'))
    with pytest.raises(ValueError, match='progression'):
        validate_content(path, config)
    md.write_text(saved)
    png = path.with_suffix('.png')
    content = bytearray(png.read_bytes())
    content[16:20] = (1599).to_bytes(4, 'big')
    png.write_bytes(content)
    with pytest.raises(ValueError, match='dimensions'):
        validate_content(path, config)


def test_regeneration_detects_stale_image_content(tmp_path: Path) -> None:
    original = Path('covers/A-flat-major_F-minor/beach-house--zebra.toml')
    path = tmp_path/original.name
    path.write_bytes(original.read_bytes())
    path.with_suffix('.png').write_bytes(original.with_suffix('.png').read_bytes())
    config = load_style(Path('config/cover-atlas.toml'))
    validate_rendered((load_entry(path),), config)
    path.write_text(path.read_text().replace('title = "Beach House — Zebra"',
                                            'title = "Changed title"'))
    with pytest.raises(ValueError, match='PNG differs'):
        validate_rendered((load_entry(path),), config)


def test_check_cli_detects_stale_index(tmp_path: Path) -> None:
    # Symlink song directories only; leave the real catalog and index untouched.
    for directory in Path('covers').iterdir():
        if directory.is_dir():
            (tmp_path/directory.name).symlink_to(directory.resolve(), target_is_directory=True)
    (tmp_path/'readme.md').write_text('stale index')
    command = [sys.executable, 'scripts/cover_library.py', '--root', str(tmp_path), '--check']
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert 'Stale cover index' in result.stderr
