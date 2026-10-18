"""One-time JSFX v2 memory import into the pinned Chord Lab CLAP state format."""
from __future__ import annotations

import base64
import math
import re
import struct


def compressed(value: int) -> bytes:
    if not 0 <= value < 2**31:
        raise ValueError('Invalid JUCE compressed integer')
    size = (value.bit_length() + 7) // 8
    return bytes([size]) + value.to_bytes(size, 'little')


def variant(value: str | float) -> bytes:
    payload = b'\x05' + value.encode() + b'\0' if isinstance(value, str) else b'\x04' + struct.pack('<d', value)
    return compressed(len(payload)) + payload


def tree(name: str, properties: tuple[tuple[str, str | float], ...], children: tuple[bytes, ...]) -> bytes:
    return (name.encode() + b'\0' + compressed(len(properties))
            + b''.join(key.encode() + b'\0' + variant(value) for key, value in properties)
            + compressed(len(children)) + b''.join(children))


def import_jsfx_state(project: str) -> bytes:
    matches = re.findall(r'<JS ChordLab/chordlab\.jsfx[^\n]*\n\s*([^\n]+)\n\s*>\s*JS_DIMS[^\n]*\n\s*<JS_SER\n(.*?)\n\s*>', project, re.S)
    if len(matches) != 1:
        raise ValueError('Expected exactly one serialized Chord Lab JSFX')
    sliders_text, memory_text = matches[0]
    sliders = [float(v) for v in sliders_text.split()[:18]]
    if len(sliders) != 18 or not all(math.isfinite(v) for v in sliders):
        raise ValueError('Invalid JSFX sliders')
    limits = ((0,11),(0,6),(0,4),(12,115),(1,127),(0,1))
    if any(not lo <= sliders[i] <= hi or not sliders[i].is_integer() for i,(lo,hi) in enumerate(limits)):
        raise ValueError('Invalid musical settings')
    if sliders[15] not in (0,1,2) or sliders[2] >= 3 + sliders[15]:
        raise ValueError('Invalid chord type/inversion')
    memory = base64.b64decode(''.join(memory_text.split()), validate=True)
    if len(memory) != 29 * 4:
        raise ValueError('Expected seven v2 voicing records')
    records = struct.unpack('<29f', memory)
    if records[0] != 2:
        raise ValueError('Only v2 voicing memory is supported')
    for i in range(1,29,4):
        valid, kind, inversion, centre = records[i:i+4]
        if (valid not in (0,1) or kind not in (0,1,2) or not 0 <= inversion < 3+kind
                or not 12 <= centre <= 115 or not inversion.is_integer() or not centre.is_integer()):
            raise ValueError('Invalid saved voicing')
    # Never replay transient held notes/commands; the dedicated CLAP owns computer input.
    for i in (6,8,9,10,11,12,16,17):
        sliders[i] = 0.0
    sliders[7], sliders[13] = 23.0, 1.0
    slider_tree = tree('sliders', tuple((str(i), v) for i,v in enumerate(sliders)), ())
    state = tree('state', (('data',base64.b64encode(memory).decode()),), (slider_tree,))
    return tree('chordlab', (('version',1.0),('engine','ysfx-0.0.47')), (state,))
