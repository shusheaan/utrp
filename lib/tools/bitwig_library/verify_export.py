"""Compare a Bitwig DAWproject export against saved REAPER sound-engine states."""
from __future__ import annotations

import argparse
import json
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from source import read_library
from states import SFIZZ_ID, sfizz_component

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'library'))
from audit_state import engine_xml, split_state, tuning_conflict


def clap_payload(data: bytes, expected_id: str) -> bytes:
    if len(data) < 8 or data[:4] != b'clap':
        raise ValueError('Invalid CLAP preset envelope')
    length = struct.unpack_from('>I', data, 4)[0]
    if length > len(data) - 8 or data[8:8 + length].decode() != expected_id:
        raise ValueError('Wrong CLAP ID or invalid length')
    return data[8 + length:]


def vst_component(data: bytes) -> bytes:
    if len(data) < 48 or data[:4] != b'VST3' or data[8:40].decode().upper() != SFIZZ_ID:
        raise ValueError('Wrong sfizz VST3 envelope')
    offset = struct.unpack_from('<q', data, 40)[0]
    if not 48 <= offset <= len(data) - 8 or data[offset:offset + 4] != b'List':
        raise ValueError('Invalid VST3 chunk list')
    count = struct.unpack_from('<i', data, offset + 4)[0]
    if not 0 <= count <= (len(data) - offset - 8) // 20:
        raise ValueError('Invalid VST3 chunk count')
    for index in range(count):
        position = offset + 8 + index * 20
        if data[position:position + 4] != b'Comp':
            continue
        start, length = struct.unpack_from('<qq', data, position + 4)
        if start < 48 or length < 0 or start + length > offset:
            raise ValueError('Invalid component range')
        return data[start:start + length]
    raise ValueError('Missing VST3 component state')


def pedal_off_appended(expected: bytes, actual: bytes, controller_count: int) -> bool:
    """Recognize only sfizz recording an explicit default CC64=0 after live input.

    All SFZ/tuning/engine bytes and original controllers must remain identical.
    This does not accept nonzero sustain or arbitrary missing/extra controllers.
    """
    offset = len(expected) - controller_count * 6 - 4
    if offset < 0 or struct.unpack_from('<I', expected, offset)[0] != controller_count:
        raise ValueError('Invalid expected sfizz controller section')
    expanded = (expected[:offset] + struct.pack('<I', controller_count + 1)
                + expected[offset + 4:] + struct.pack('<Hf', 64, 0.0))
    return actual == expanded


def compare(source: Path, exported: Path) -> tuple[dict[str, object], ...]:
    library = read_library(source)
    rows: list[dict[str, object]] = []
    with zipfile.ZipFile(exported) as archive:
        root = ET.fromstring(archive.read('project.xml'))
        tracks: dict[str, ET.Element] = {}
        for track in root.findall('.//Track'):
            name = track.get('name', '')
            if name in tracks:
                raise ValueError(f'Duplicate exported track name: {name}')
            tracks[name] = track
        for sound in library.sounds:
            track = tracks.get(sound.name)
            if track is None:
                raise ValueError(f'Missing exported track: {sound.name}')
            kind = 'Vst3Plugin' if sound.plugin == 'sfizz' else 'ClapPlugin'
            state = track.find(f'Channel/Devices/{kind}/State')
            if state is None:
                raise ValueError(f'Missing exported state: {sound.name}')
            payload = archive.read(state.attrib['path'])
            if sound.plugin == 'sfizz':
                actual = vst_component(payload)
                expected = sfizz_component(sound)
                identical = actual == expected
                pedal_off = (64 not in dict(sound.controllers) and
                             pedal_off_appended(expected, actual, len(sound.controllers)))
                rows.append({'name': sound.name, 'component_equal': identical,
                             'equivalent': identical or pedal_off,
                             'runtime_difference': 'explicit default CC64=0 appended' if pedal_off else ''})
            else:
                actual, tail = split_state(clap_payload(payload, sound.plugin))
                expected, expected_tail = split_state(sound.state)
                rows.append({'name': sound.name, 'engine_equal': engine_xml(actual) == engine_xml(expected),
                             'wavetables_equal': tail == expected_tail,
                             'tuning_mode_consistent': not tuning_conflict(actual)})
    return tuple(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('exported', type=Path)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    rows = compare(args.source, args.exported)
    args.report.write_text(json.dumps(rows, indent=2) + '\n')
    failed = [r['name'] for r in rows
              if not r.get('equivalent', all(v is not False for v in r.values()))]
    print(f'{len(rows)} compared; review required: {failed}')
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
