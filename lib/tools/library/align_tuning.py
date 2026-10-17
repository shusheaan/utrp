"""Write a new library copy aligning host tuning to each patch; never overwrite."""
from __future__ import annotations

import argparse
import base64
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

from lib.tools.library.audit_state import split_state, tuning_conflict


def align_state(raw: bytes) -> bytes:
    root, waveforms = split_state(raw)
    if not tuning_conflict(root):
        return raw
    patch = root.find('nonparamconfig/tuningApplicationMode')
    extra = root.find('dawExtraState')
    assert patch is not None and extra is not None
    value = patch.get('v')
    assert value is not None
    host = extra.find('tuningApplicationMode')
    if host is None:
        host = ET.SubElement(extra, 'tuningApplicationMode')
    host.set('v', value)
    xml = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    return raw[:4] + struct.pack('<I', len(xml)) + raw[8:32] + xml + waveforms


def align_project(text: str) -> tuple[str, tuple[str, ...]]:
    blocks = text.split('  <TRACK ')
    changes: list[str] = []
    identities: set[str] = set()
    for index, block in enumerate(blocks[1:], 1):
        marker = re.search(r'^\s*utrp_patch (.+)$', block, re.M)
        if marker is None:
            continue
        identity = marker[1].strip().strip('"')
        if identity in identities:
            raise ValueError(f'Duplicate library patch: {identity}')
        identities.add(identity)
        if 'http://sfztools.github.io/sfizz "' in block:
            continue  # sfizz does not contain Surge host tuning state.
        if 'org.surge-synth-team.surge-xt "' not in block:
            raise ValueError(f'Expected Surge CLAP track: {identity}')
        states = list(re.finditer(r'(?m)^([ \t]*)<STATE\r?\n([A-Za-z0-9+/= \t\r\n]+?)^[ \t]*>', block))
        if len(states) != 1:
            raise ValueError(f'Expected exactly one CLAP state: {identity}')
        state = states[0]
        raw = base64.b64decode(''.join(state[2].split()), validate=True)
        updated = align_state(raw)
        if updated == raw:
            continue
        encoded = base64.b64encode(updated).decode('ascii')
        newline = '\r\n' if '\r\n' in state[0] else '\n'
        body = ''.join(state[1] + '  ' + encoded[i:i + 128] + newline
                       for i in range(0, len(encoded), 128))
        blocks[index] = block[:state.start(2)] + body + block[state.end(2):]
        changes.append(identity)
    if not identities:
        raise ValueError('No marked library tracks')
    return '  <TRACK '.join(blocks), tuple(changes)


def write_copy(source: Path, destination: Path) -> tuple[str, ...]:
    text, changes = align_project(source.read_bytes().decode('utf-8'))
    with destination.open('xb') as output:
        output.write(text.encode('utf-8'))
    return changes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    changes = write_copy(args.source, args.destination)
    print(f'Aligned {len(changes)} host tuning fields; source untouched: {args.destination}')


if __name__ == '__main__':
    main()
