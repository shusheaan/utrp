from pathlib import Path
import hashlib
import json
import tarfile
import zipfile

import pytest

from prepare_build import assets, dependencies, extract, keyboard_map, patch_midi, patch_global_parameters, prepare
from port_upstream import replace_once
from stage_port import stage

HERE = Path(__file__).parent


def test_dependency_pins() -> None:
    deps = dependencies(HERE / 'dependencies.toml')
    assert len(deps) == 6
    assert len({dep.name for dep in deps}) == 6
    for dep in deps:
        assert dep.url.startswith('https://codeload.github.com/')
        assert len(bytes.fromhex(dep.sha256)) == 32
        assert not Path(dep.destination).is_absolute()
        assert '..' not in Path(dep.destination).parts


def test_assets_unchanged_and_deterministic(tmp_path: Path) -> None:
    source = HERE.parent / 'chordlab'
    paths = (tmp_path / 'a.zip', tmp_path / 'b.zip')
    for path in paths:
        assets(source, path, HERE / 'prototype.toml')
    assert paths[0].read_bytes() == paths[1].read_bytes()
    with zipfile.ZipFile(paths[0]) as archive:
        assert len(archive.namelist()) == 11
        for name in archive.namelist():
            assert archive.read(name) == (source / name).read_bytes()


def test_keyboard_mapping_generated(tmp_path: Path) -> None:
    output = tmp_path / 'keyboard_map.h'
    source = HERE / 'keyboard-map.txt'
    keyboard_map(source, output)
    for line in source.read_text().splitlines():
        if line.strip() and not line.startswith(';'):
            key, offset = map(int, line.split())
            assert f'KeyBinding{{{key}, {60 + offset}}}' in output.read_text()


def test_duplicate_mapping_rejected(tmp_path: Path) -> None:
    source = tmp_path / 'map.txt'
    source.write_text('65 1\n65 2\n')
    with pytest.raises(ValueError, match='Duplicate'):
        keyboard_map(source, tmp_path / 'output')


@pytest.mark.parametrize('text', ['missing', 'one one'])
def test_patch_fails_on_changed_source(text: str) -> None:
    with pytest.raises(ValueError, match='mismatch'):
        replace_once(text, 'one', 'two')


def test_patch_adapter_rejects_wrong_version(tmp_path: Path) -> None:
    path = tmp_path / 'src/wrapper/clap-juce-wrapper.cpp'
    path.parent.mkdir(parents=True)
    path.write_text('unknown adapter')
    with pytest.raises(ValueError, match='no longer matches'):
        patch_midi(tmp_path)
    assert path.read_text() == 'unknown adapter'


def test_dependencies_validated_before_output(tmp_path: Path) -> None:
    for dep in dependencies(HERE / 'dependencies.toml'):
        (tmp_path / f'{dep.name}.tar.gz').write_bytes(b'invalid')
    output = tmp_path / 'output'
    with pytest.raises(ValueError, match='SHA-256'):
        prepare(tmp_path, output, HERE)
    assert not output.exists()


def test_tar_traversal_rejected(tmp_path: Path) -> None:
    archive = tmp_path / 'archive.tar.gz'
    with tarfile.open(archive, 'w:gz') as bundle:
        info = tarfile.TarInfo('../../escape')
        bundle.addfile(info)
    with pytest.raises(tarfile.FilterError):
        extract(archive, tmp_path / 'output')
    assert not (tmp_path / 'output').exists()


def test_stage_dedicated_port(tmp_path: Path) -> None:
    plugin = tmp_path / 'Chord Lab.clap'
    plugin.write_bytes(b'test fixture, not an actual plugin')
    output = stage(plugin, tmp_path / 'profile', HERE)
    manifest = json.loads((output / 'manifest.json').read_text())
    assert manifest['plugin_id'] == 'org.utrp.chordlab'
    assert manifest['plugin_sha256'] == hashlib.sha256(plugin.read_bytes()).hexdigest()
    assert 'org.utrp.chordlab' in (output / 'wrapper-track.txt').read_text()
    assert '<STATE' not in (output / 'wrapper-track.txt').read_text()
    assert 'linux_audio_mode=2' in (output / 'reaper/reaper.ini').read_text()
    for name, digest in manifest['source_sha256'].items():
        assert hashlib.sha256((output / 'reaper/Effects/ChordLab' / name).read_bytes()).hexdigest() == digest
    with pytest.raises(FileExistsError):
        stage(plugin, output, HERE)


def test_stage_rejects_missing_binary(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        stage(tmp_path / 'missing.clap', tmp_path / 'output', HERE)
    assert not (tmp_path / 'output').exists()


def test_linux_font_pixel_height_backport() -> None:
    from port_upstream import font_source
    fixture = ('  if (lfHeight<0) lfHeight=-lfHeight;\n'
               '      FT_Set_Char_Size(face,lfWidth*64, lfHeight*64,0,0); // 72dpi')
    patched = font_source(fixture)
    assert 'face->units_per_EM' in patched and '/ face->height' in patched
    assert ': -lfHeight * 64' in patched
    assert 'if (lfHeight<0)' not in patched
    with pytest.raises(ValueError, match='mismatch'):
        font_source(patched)


def test_one_hand_mapping() -> None:
    mapping = dict(tuple(map(int, line.split())) for line in
                   (HERE / 'keyboard-map.txt').read_text().splitlines()
                   if line.strip() and not line.startswith(';'))
    assert mapping[72] == 19  # H: left while holding a chord
    assert mapping[76] == 20  # L: right while holding a chord
    assert mapping[74] == 28 and mapping[75] == 29
    assert mapping[32] == 22  # Space: Sustain toggle, no longer reset
    assert mapping[13] == 21  # Enter: current chord/current mode only
    assert mapping[9] == 25   # Tab: chord type remains
    assert not {27, 71, 86, 59}.intersection(mapping)  # G/V/semicolon retired
    assert tuple(mapping[key] for key in (90, 88, 67, 65, 83, 68, 70)) == tuple(range(12, 19))


def test_global_parameter_event_uses_wildcards(tmp_path: Path) -> None:
    path = tmp_path / "src/wrapper/clap-juce-wrapper.cpp"
    path.parent.mkdir(parents=True)
    path.write_text("                evt.value = pc.newval;\n" + "\n".join(
        "uiParamChangeQ.push({" + kind + ", 0, id, value});"
        for kind in ("CLAP_EVENT_PARAM_VALUE", "CLAP_EVENT_PARAM_GESTURE_BEGIN", "CLAP_EVENT_PARAM_GESTURE_END")
    ))
    patch_global_parameters(tmp_path)
    assert path.read_text().count("CLAP_EVENT_IS_LIVE") == 3
    assert "evt.note_id = -1;" in path.read_text()
    assert "evt.port_index = evt.channel = evt.key = -1;" in path.read_text()
    with pytest.raises(ValueError, match="global-parameter"):
        patch_global_parameters(tmp_path)


def test_no_standalone_modifier_commands() -> None:
    source = (HERE / 'physical_keys.cpp').read_text()
    assert 'controlTap' not in source
    assert 'shiftTap' not in source
    assert 'ShiftMask' in source
    assert 'ControlMask' in source  # Ctrl combinations still suppress commands.
