"""A host tuning override must not disappear with cosmetic XML normalization."""
import base64
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from lib.tools.library.audit_state import audit, engine_xml, tuning_conflict


def state(patch: str = '0', host: str = '1', populated: str = '1') -> ET.Element:
    return ET.fromstring(
        f'<patch><nonparamconfig><tuningApplicationMode v="{patch}" />'
        f'</nonparamconfig><dawExtraState populated="{populated}">'
        f'<tuningApplicationMode v="{host}" /></dawExtraState></patch>'
    )


@pytest.mark.parametrize('patch,host,expected', [('0', '1', True), ('1', '0', True),
                                                ('0', '0', False), ('1', '1', False)])
def test_host_tuning_override(patch: str, host: str, expected: bool) -> None:
    assert tuning_conflict(state(patch, host)) is expected


def test_unpopulated_host_does_not_override() -> None:
    assert not tuning_conflict(state(populated='0'))
    assert not tuning_conflict(ET.fromstring('<patch />'))


def test_missing_host_mode_uses_surge_default() -> None:
    root = state()
    extra = root.find('dawExtraState')
    assert extra is not None
    extra.clear()
    extra.set('populated', '1')
    assert tuning_conflict(root)


@pytest.mark.parametrize('patch,host', [('2', '1'), ('0', 'bad')])
def test_invalid_mode_is_not_silently_ignored(patch: str, host: str) -> None:
    with pytest.raises(ValueError, match='tuning'):
        tuning_conflict(state(patch, host))


def test_normalization_does_not_mutate_or_hide_conflict() -> None:
    root = state()
    before = ET.tostring(root)
    engine_xml(root)
    assert ET.tostring(root) == before
    assert tuning_conflict(root)


def test_audit_reports_conflict_despite_equal_patch_and_waveforms(tmp_path: Path) -> None:
    xml = ET.tostring(state())
    raw = b'sub3' + struct.pack('<I', len(xml)) + bytes(24) + xml + b'waveform'
    fxp = tmp_path / 'example.fxp'
    fxp.write_bytes(bytes(60) + raw)
    project = tmp_path / 'test.rpp'
    project.write_text(
        '  <TRACK {test}\n    utrp_patch example\n'
        f'    utrp_patch_source "{fxp}"\n'
        f'    <STATE\n      {base64.b64encode(raw).decode()}\n    >\n  >\n'
    )
    row, = audit(project)
    assert row.engine_equal and row.wavetables_equal
    assert row.tuning_conflict
    # Mixed library: known sampled pianos are outside the Surge binary audit.
    with project.open('a') as stream:
        stream.write('  <TRACK {piano}\n    utrp_patch basic/piano\n'
                     '    utrp_patch_source /samples/piano.sfz\n'
                     '    <LV2 "LV2i: sfizz" http://sfztools.github.io/sfizz ""\n'
                     '    >\n  >\n')
    assert audit(project) == (row,)
    project.write_text(project.read_text().replace('http://sfztools.github.io/sfizz', 'unknown'))
    with pytest.raises(ValueError, match='Expected sfizz'):
        audit(project)
