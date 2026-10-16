"""Migration boundaries: preserve all payload bytes and never overwrite edits."""
import importlib.util
import struct
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("library_prepare", Path(__file__).with_name("prepare.py"))
assert _spec and _spec.loader
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
surge_payload = _module.surge_payload
prepare = _module.prepare


def fixture_bytes() -> bytes:
    xml = b'<patch><parameters><volume value="1" /></parameters></patch>'
    raw = b'sub3' + struct.pack('<I', len(xml)) + bytes(24) + xml + b'WAVETABLE\x00\xff'
    header = bytearray(60)
    for at, value in ((0, b'CcnK'), (8, b'FPCh'), (16, b'cjs3')):
        header[at:at + 4] = value
    struct.pack_into('>I', header, 56, len(raw))
    return bytes(header) + raw


def test_preserves_binary_tail() -> None:
    data = fixture_bytes()
    assert surge_payload(data) == data[60:]
    assert surge_payload(data).endswith(b'WAVETABLE\x00\xff')


@pytest.mark.parametrize('data', [b'', b'CcnK', fixture_bytes()[:-1], b'bad!' + fixture_bytes()[4:]])
def test_rejects_invalid_payload(data: bytes) -> None:
    with pytest.raises(ValueError):
        surge_payload(data)


def test_refuses_existing_project(tmp_path: Path) -> None:
    project = tmp_path / 'synth.rpp'
    project.write_text('user edits')
    config = tmp_path / 'library.toml'
    config.write_text('patch_root = "patches"\nproject = "synth.rpp"\n')
    with pytest.raises(FileExistsError):
        prepare(config, tmp_path / 'stage')
    assert project.read_text() == 'user edits'
    assert not (tmp_path / 'stage').exists()


def test_invalid_patch_leaves_no_staging(tmp_path: Path) -> None:
    root = tmp_path / 'patches'
    root.mkdir()
    (root / 'bad.fxp').write_bytes(b'bad')
    config = tmp_path / 'library.toml'
    config.write_text('patch_root="patches"\nproject="synth.rpp"\ntrack_volume=0.1\nmaster_volume=0.5\ninitial_patch="patches/bad"\n')
    with pytest.raises(ValueError):
        prepare(config, tmp_path / 'stage')
    assert not (tmp_path / 'stage').exists()
