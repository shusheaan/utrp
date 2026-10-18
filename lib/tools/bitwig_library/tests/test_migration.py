from __future__ import annotations

import base64
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build import inventory, write_project
from source import Library, Sound, read_library
from states import SFIZZ_ID, clap_preset, sfizz_component, vst3_preset


def minimal_rpp(tmp_path: Path) -> Path:
    patch = tmp_path / 'patch with spaces.fxp'
    patch.write_bytes(b'patch')
    state = base64.b64encode(b'sub3saved-state').decode()
    chord = base64.b64encode(b'chordlab-state').decode()
    text = f'''<REAPER_PROJECT 0.1 "test"
  MASTER_VOLUME 0.8 0
  TEMPO 120 4 4
  <TRACK {{shared}}
    NAME "CHORD LAB"
    VOLPAN 1 0
    ISBUS 0 0
      <CLAP "Chord Lab" org.utrp.chordlab ""
        <STATE
          {chord}
        >
      >
  >
  <TRACK {{group}}
    NAME "Test group"
    VOLPAN 0.9 -0.2
    ISBUS 1 1
  >
  <TRACK {{sound}}
    NAME "Sound"
    VOLPAN 0.1 0.2
    ISBUS 2 -1
      <CLAP "Surge" org.surge-synth-team.surge-xt ""
        <STATE
          {state}
        >
      >
    <EXT
      utrp_patch "test/sound"
      utrp_patch_source "{patch}"
    >
  >
>
'''
    project = tmp_path / 'source.rpp'
    project.write_text(text)
    return project


def test_saved_state_not_old_fxp(tmp_path: Path) -> None:
    path = minimal_rpp(tmp_path)
    original = path.read_bytes()
    library = read_library(path)
    assert library.master_gain == .8
    assert library.groups == (('Test group', .9, -.2),)
    assert library.sounds[0].state == b'sub3saved-state'
    assert library.sounds[0].gain == .1
    assert library.sounds[0].pan == .2
    assert path.read_bytes() == original


def test_reject_invalid_base64(tmp_path: Path) -> None:
    path = minimal_rpp(tmp_path)
    path.write_text(path.read_text().replace(base64.b64encode(b'sub3saved-state').decode(), '!!broken'))
    with pytest.raises(ValueError):
        read_library(path)


def test_reject_unknown_track(tmp_path: Path) -> None:
    path = minimal_rpp(tmp_path)
    path.write_text(path.read_text().replace('utrp_patch ', 'unknown_marker '))
    with pytest.raises(ValueError, match='Unaccounted track'):
        read_library(path)


def test_clap_envelope() -> None:
    payload = clap_preset('org.test', b'raw')
    assert payload == b'clap\x00\x00\x00\x08org.testraw'
    with pytest.raises(ValueError):
        clap_preset('', b'raw')


def test_vst3_chunk_offsets() -> None:
    data = vst3_preset(SFIZZ_ID, b'component')
    assert data[:4] == b'VST3'
    assert data[8:40] == SFIZZ_ID.encode()
    offset = struct.unpack_from('<q', data, 40)[0]
    assert data[offset:offset + 4] == b'List'
    assert data[offset + 8:offset + 12] == b'Comp'
    assert struct.unpack_from('<qq', data, offset + 12) == (48, 9)
    assert data[48:offset] == b'component'


def test_archive_preserves_state_and_groups(tmp_path: Path) -> None:
    library = read_library(minimal_rpp(tmp_path))
    target = tmp_path / 'Library.dawproject'
    write_project(library, target)
    with zipfile.ZipFile(target) as archive:
        root = ET.fromstring(archive.read('project.xml'))
        group = root.find("Structure/Track[@name='Test group']")
        assert group is not None and group.get('contentType') == 'tracks'
        sound = group.find('Track')
        assert sound is not None and sound.get('name') == 'Sound'
        state = sound.find('Channel/Devices/ClapPlugin/State')
        assert state is not None
        assert archive.read(state.attrib['path']).endswith(b'sub3saved-state')
        guitar = root.find("Structure/Track[@id='guitar']/Channel/Devices/ClapPlugin/State")
        assert guitar is not None
        assert b'GFRONT\x01\0' in archive.read(guitar.attrib['path'])
    with pytest.raises(FileExistsError):
        write_project(library, target)


def test_actual_local_inventory() -> None:
    path = Path.home() / 'storage/daw/synth.rpp'
    if not path.exists():
        pytest.skip('Local Library fixture not installed')
    library = read_library(path)
    assert len(library.sounds) == 95
    assert sum(s.plugin == 'sfizz' for s in library.sounds) == 2
    report = inventory(library, Path(__file__).resolve().parents[4])
    assert report['repo_fxp_count'] == 88
    assert report['missing_repo_fxp'] == []
    assert library.sounds[0].sfz is not None
    assert library.sounds[0].sfz.name == 'SalamanderGrandPianoV3Retuned.sfz'
    component = sfizz_component(library.sounds[1])
    assert struct.unpack_from('<Q', component)[0] == 5
    assert str(library.sounds[1].sfz).encode() in component
    assert component.endswith(struct.pack('<Hf', 11, 1))
    bad = replace(library.sounds[1], parameters=(('unknown', 1.0),))
    with pytest.raises(ValueError, match='Unexpected sfizz'):
        sfizz_component(bad)


def test_round_trip_envelopes() -> None:
    from verify_export import clap_payload, vst_component
    assert clap_payload(clap_preset('org.test', b'payload'), 'org.test') == b'payload'
    assert vst_component(vst3_preset(SFIZZ_ID, b'component')) == b'component'
    with pytest.raises(ValueError):
        clap_payload(clap_preset('org.test', b'payload'), 'wrong')
    with pytest.raises(ValueError):
        vst_component(b'VST3')


def test_truncated_clap_envelope() -> None:
    from verify_export import clap_payload
    with pytest.raises(ValueError):
        clap_payload(b'clap' + struct.pack('>I', 100) + b'x', 'x')


def test_corrupt_vst_chunk_range() -> None:
    from verify_export import vst_component
    data = bytearray(vst3_preset(SFIZZ_ID, b'component'))
    struct.pack_into('<q', data, len(data) - 8, 999999)
    with pytest.raises(ValueError):
        vst_component(bytes(data))


def test_sfizz_runtime_pedal_off_is_narrowly_recognized() -> None:
    from verify_export import pedal_off_appended
    controllers = struct.pack('<Hf', 7, 1.0)
    expected = b'engine' + struct.pack('<I', 1) + controllers
    actual = b'engine' + struct.pack('<I', 2) + controllers + struct.pack('<Hf', 64, 0.0)
    assert pedal_off_appended(expected, actual, 1)
    assert not pedal_off_appended(expected, actual[:-4] + struct.pack('<f', 1.0), 1)
    assert not pedal_off_appended(expected, b'broken' + actual[6:], 1)
    assert not pedal_off_appended(expected, actual + struct.pack('<Hf', 1, 0.0), 1)
    with pytest.raises(ValueError):
        pedal_off_appended(expected, actual, 99)
