"""Compare every library CLAP state with its source FXP, including binary wavetables."""
from __future__ import annotations

import argparse
import base64
import json
import re
import struct
import xml.etree.ElementTree as ET
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class PatchAudit:
    patch: str
    source: str
    engine_equal: bool
    wavetables_equal: bool
    tuning_conflict: bool


def split_state(data: bytes) -> tuple[ET.Element, bytes]:
    if len(data) < 32 or data[:4] != b'sub3':
        raise ValueError('Invalid Surge raw state')
    size = struct.unpack_from('<I', data, 4)[0]
    if not 0 < size <= len(data) - 32:
        raise ValueError('Invalid state XML length')
    return ET.fromstring(data[32:32 + size]), data[32 + size:]


def engine_xml(root: ET.Element) -> bytes:
    # Compare patch content, not host serialization. Host tuning is checked separately;
    # dawExtraState is NOT purely cosmetic (it can override patch tuning on GUI open).
    root = deepcopy(root)
    extra = root.find('dawExtraState')
    if extra is not None:
        root.remove(extra)
    for node in root.iter():
        if node.get('deform_type') == '0':
            del node.attrib['deform_type']
        attrs = sorted(node.attrib.items())
        node.attrib.clear()
        node.attrib.update(attrs)
        node.text = (node.text or '').strip() or None
        node.tail = None
    return ET.tostring(root)


def tuning_conflict(root: ET.Element) -> bool:
    """Detect a populated host state that overrides the patch's explicit tuning mode."""
    patch = root.find('nonparamconfig/tuningApplicationMode')
    extra = root.find('dawExtraState')
    if patch is None or extra is None or extra.get('populated') != '1':
        return False
    host = extra.find('tuningApplicationMode')
    # Surge 1.3.4 defaults a missing host mode to RETUNE_MIDI_ONLY when restoring.
    patch_value = patch.get('v')
    host_value = '1' if host is None else host.get('v')
    if patch_value not in ('0', '1') or host_value not in ('0', '1'):
        raise ValueError('Invalid Surge tuning application mode')
    return patch_value != host_value


def audit(project: Path, loaded: Path | None = None) -> tuple[PatchAudit, ...]:
    rows: list[PatchAudit] = []
    for index, block in enumerate(project.read_text().split('  <TRACK ')[1:]):
        marker = re.search(r'utrp_patch (.+)', block)
        if marker is None:
            continue
        source = re.search(r'utrp_patch_source (.+)', block)
        # Sampled pianos have no Surge patch/tuning payload to compare.
        if source is not None and Path(source[1].strip().strip('"')).suffix == '.sfz':
            if 'http://sfztools.github.io/sfizz "' not in block:
                raise ValueError('Expected sfizz for SFZ library track')
            continue
        state = re.search(r'<STATE\n(.*?)\n\s*>', block, re.S)
        if source is None or state is None:
            raise ValueError('Incomplete library track')
        path = Path(source[1].strip().strip('"'))
        payload = path.read_bytes()[60:]
        encoded = (loaded / f'loaded-{index}.b64').read_text() if loaded else state[1]
        actual = base64.b64decode(''.join(encoded.split()), validate=True)
        expected_xml, expected_tail = split_state(payload)
        actual_xml, actual_tail = split_state(actual)
        rows.append(PatchAudit(marker[1].strip().strip('"'), str(path),
                               engine_xml(expected_xml) == engine_xml(actual_xml),
                               expected_tail == actual_tail, tuning_conflict(actual_xml)))
    if not rows or len({r.patch for r in rows}) != len(rows):
        raise ValueError('Empty inventory or duplicate patch identity')
    return tuple(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('report', type=Path)
    parser.add_argument('--loaded', type=Path)
    args = parser.parse_args()
    rows = audit(args.project, args.loaded)
    args.report.write_text(json.dumps([asdict(row) for row in rows], indent=2) + '\n')
    failures = [row.patch for row in rows
                if not row.engine_equal or not row.wavetables_equal or row.tuning_conflict]
    print(f'{len(rows)} patches; mismatches: {failures}')
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
