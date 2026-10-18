import base64
import struct

import pytest

from lib.tools.chordlab_clap.migrate_state import compressed, import_jsfx_state


def fixture() -> str:
    data=base64.b64encode(struct.pack('<29f',2,*([1,2,3,62]*7))).decode()
    return '<JS ChordLab/chordlab.jsfx "Chord Lab"\n4 6 0 60 64 1 145 23 0 0 0 0 0 0 68 1 0 0 -\n>\nJS_DIMS 884 631\n<JS_SER\n'+data+'\n>'


def test_preserves_memory_and_settings() -> None:
    result=import_jsfx_state(fixture())
    assert result.startswith(b'chordlab\0')
    assert base64.b64encode(struct.pack('<29f',2,*([1,2,3,62]*7))) in result
    assert b'0\0\x01\x09\x04'+struct.pack('<d',4) in result
    assert b'13\0\x01\x09\x04'+struct.pack('<d',1) in result
    assert b'6\0\x01\x09\x04'+struct.pack('<d',0) in result


@pytest.mark.parametrize('text',['',fixture()+fixture(),fixture().replace('4 6 0','nan 6 0'),fixture().replace('4 6 0','12 6 0')])
def test_rejects_invalid_source(text: str) -> None:
    with pytest.raises(ValueError):
        import_jsfx_state(text)


def test_compressed_bounds() -> None:
    assert compressed(0)==b'\0'
    assert compressed(256)==b'\x02\x00\x01'
    with pytest.raises(ValueError):
        compressed(-1)
