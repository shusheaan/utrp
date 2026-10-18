"""Keep the sole product entry and engine dependencies explicit after retirement."""
from pathlib import Path
import tomllib

HERE = Path(__file__).parent
ENGINE = HERE.parent / 'chordlab'


def test_retired_product_entry_points_are_absent() -> None:
    for name in ('install.py', 'Chord Lab mode.lua', 'Open Chord Lab.lua',
                 'Cycle chord type.lua', 'Register Chord Lab.lua', 'reaper-vkbmap.txt'):
        assert not (ENGINE / name).exists()
    assert not (HERE / 'prototype.py').exists()


def test_current_embedded_assets_remain_available() -> None:
    config = tomllib.loads((HERE / 'prototype.toml').read_text())
    for name in config['source']['assets']:
        assert (ENGINE / name).is_file()
    assert (ENGINE / 'generate_theme.py').is_file()
    assert (HERE / 'keyboard-map.txt').is_file()


def test_current_open_action_does_not_install_or_launch_legacy() -> None:
    source = (HERE / 'Open Chord Lab.lua').read_text()
    assert 'org.utrp.chordlab' in source
    assert 'TrackFX_Show' in source
    assert 'AddRemoveReaScript' not in source
    assert 'TrackFX_AddByName' not in source
    assert 'Chord Lab mode.lua' not in source
