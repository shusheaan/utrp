"""Repair copies preserve musical parameters, waveforms and unrelated project data."""
import base64
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from lib.tools.library.align_tuning import align_project, align_state, write_copy
from lib.tools.library.audit_state import split_state, tuning_conflict


def payload(host: int = 1) -> bytes:
    xml = (
        '<patch><parameters><cutoff value="0.731" /></parameters>'
        '<nonparamconfig><tuningApplicationMode v="0" /></nonparamconfig>'
        f'<dawExtraState populated="1"><tuningApplicationMode v="{host}" />'
        '<hasTuning v="1" /><tuningContents v="custom scale" />'
        '<editor current_scene="1" /></dawExtraState></patch>'
    ).encode()
    return b'sub3' + struct.pack('<I', len(xml)) + bytes(range(24)) + xml + b'\x00wave\xff'


def project(raw: bytes, newline: str = '\n') -> str:
    return newline.join([
        '<REAPER_PROJECT 0.1', '  MASTER_VOLUME 0.70794578438414', '  <TRACK {synth}',
        '    NAME "my edited patch"', '    utrp_patch album/patch',
        '    <CLAP "CLAPi: Surge XT (Surge Synth Team)" org.surge-synth-team.surge-xt ""',
        '      <STATE', '        ' + base64.b64encode(raw).decode(), '      >', '    >',
        '  >', '  <TRACK {audio}', '    NAME "do not touch"', '  >', '>', '',
    ])


def test_only_host_tuning_semantics_change() -> None:
    raw = payload()
    updated = align_state(raw)
    before, tail = split_state(raw)
    after, new_tail = split_state(updated)
    mode = before.find('dawExtraState/tuningApplicationMode')
    assert mode is not None
    mode.set('v', '0')
    assert ET.tostring(before) == ET.tostring(after)
    assert tail == new_tail and raw[8:32] == updated[8:32]
    assert not tuning_conflict(after)
    assert align_state(updated) == updated


def test_matching_state_is_byte_identical() -> None:
    raw = payload(host=0)
    assert align_state(raw) == raw


@pytest.mark.parametrize('newline', ['\n', '\r\n'])
def test_project_changes_only_state_body(newline: str) -> None:
    text = project(payload(), newline)
    updated, changed = align_project(text)
    assert changed == ('album/patch',)
    start = text.index('      <STATE')
    assert text[:start] == updated[:start]
    assert text[text.index('      >', start):] == updated[updated.index('      >', start):]
    assert align_project(updated) == (updated, ())
    if newline == '\r\n':
        assert '\n' not in updated.replace('\r\n', '')


def test_copy_refuses_overwrite_and_keeps_source(tmp_path: Path) -> None:
    source, destination = tmp_path / 'source.rpp', tmp_path / 'candidate.rpp'
    data = project(payload()).encode()
    source.write_bytes(data)
    assert write_copy(source, destination) == ('album/patch',)
    assert source.read_bytes() == data
    with pytest.raises(FileExistsError):
        write_copy(source, destination)
    with pytest.raises(FileExistsError):
        write_copy(source, source)


@pytest.mark.parametrize('text', ['<REAPER_PROJECT>', project(payload()).replace(
    'org.surge-synth-team.surge-xt', 'different-plugin')])
def test_invalid_input_creates_nothing(tmp_path: Path, text: str) -> None:
    source, destination = tmp_path / 'bad.rpp', tmp_path / 'out.rpp'
    source.write_text(text)
    with pytest.raises(ValueError):
        write_copy(source, destination)
    assert not destination.exists()
