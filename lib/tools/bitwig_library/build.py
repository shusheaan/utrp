"""Build a non-destructive Bitwig import candidate from the saved REAPER library."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import tomllib
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import replace
from pathlib import Path

from source import Library, read_library
from states import SFIZZ_ID, clap_preset, sfizz_component, vst3_preset


def channel(parent: ET.Element, identity: str, name: str, destination: str | None,
            gain: float, pan: float, loaded: bool = True, role: str = 'regular') -> ET.Element:
    track = ET.SubElement(parent, 'Track', id=identity, name=name, contentType='notes',
                          loaded=str(loaded).lower())
    attrs = dict(id=identity + '_channel', audioChannels='2', role=role, solo='false')
    if destination:
        attrs['destination'] = destination
    ch = ET.SubElement(track, 'Channel', attrs)
    ET.SubElement(ch, 'Devices')
    ET.SubElement(ch, 'Mute', value='false')
    ET.SubElement(ch, 'Pan', unit='normalized', value=str((pan + 1) / 2), min='0', max='1')
    ET.SubElement(ch, 'Volume', unit='linear', value=str(gain), min='0', max=str(max(2, gain)))
    return track


def device(track: ET.Element, identity: str, plugin_id: str, name: str,
           role: str, state_path: str | None, vst3: bool = False) -> None:
    devices = track.find('Channel/Devices')
    if devices is None:
        raise ValueError('Missing channel devices')
    plugin = ET.SubElement(devices, 'Vst3Plugin' if vst3 else 'ClapPlugin', id=identity,
                           deviceID=plugin_id, deviceName=name, name=name,
                           deviceRole=role, loaded='true')
    ET.SubElement(plugin, 'Enabled', value='true')
    if state_path:
        ET.SubElement(plugin, 'State', path=state_path)


def write_project(library: Library, destination: Path) -> None:
    root = ET.Element('Project', version='1.0')
    ET.SubElement(root, 'Application', name='UTRP Library migration', version='0.1')
    transport = ET.SubElement(root, 'Transport')
    ET.SubElement(transport, 'Tempo', unit='bpm', value=str(library.tempo))
    ET.SubElement(transport, 'TimeSignature', numerator='4', denominator='4')
    structure = ET.SubElement(root, 'Structure')
    chord = channel(structure, 'shared_chord', 'CHORD LAB - shared MIDI input',
                    'master_channel', 1, 0)
    device(chord, 'chord_device', 'org.utrp.chordlab', 'Chord Lab', 'noteFX',
           'plugins/chord.clap-preset')
    payloads: dict[str, bytes] = {'plugins/chord.clap-preset':
                                clap_preset('org.utrp.chordlab', library.chord_state)}
    groups: dict[str, ET.Element] = {}
    for index, (name, gain, pan) in enumerate(library.groups):
        group = channel(structure, f'group_{index}', name, 'master_channel', gain, pan, role='submix')
        group.set('contentType', 'tracks')
        groups[name] = group
    for index, sound in enumerate(library.sounds):
        identity = f'sound_{index:03d}'
        group = groups[sound.group]
        track = channel(group, identity, sound.name, group.get('id') + '_channel',
                        sound.gain, sound.pan, loaded=index == 0)
        track.set('comment', 'UTRP Library | ' + sound.identity)
        path = f'plugins/{identity}'
        if sound.plugin == 'sfizz':
            path += '.vstpreset'
            payloads[path] = vst3_preset(SFIZZ_ID, sfizz_component(sound))
            device(track, identity + '_device', SFIZZ_ID, 'sfizz', 'instrument', path, vst3=True)
        else:
            path += '.clap-preset'
            payloads[path] = clap_preset(sound.plugin, sound.state)
            device(track, identity + '_device', sound.plugin, 'Surge XT', 'instrument', path)
    guitar = channel(structure, 'guitar', 'GUITAR - raw detection', None, 0, 0)
    guitar.set('contentType', 'audio')
    defaults = tomllib.loads((Path(__file__).parent.parent / 'guitar_frontend/defaults.toml').read_text())['parameters']
    raw_guitar = b'GFRONT\x01\0' + struct.pack('<7d', *(defaults[k] for k in (
        'enabled', 'gate_db', 'confidence', 'stability_ms', 'release_ms', 'velocity', 'input_channel')))
    payloads['plugins/guitar.clap-preset'] = clap_preset('org.utrp.guitar-frontend', raw_guitar)
    device(guitar, 'guitar_frontend', 'org.utrp.guitar-frontend', 'Guitar Frontend', 'noteFX', 'plugins/guitar.clap-preset')
    device(guitar, 'guitar_chord', 'org.utrp.chordlab', 'Chord Lab', 'noteFX', 'plugins/chord.clap-preset')
    channel(structure, 'master', 'Master', None, library.master_gain, 0, role='master')
    arrangement = ET.SubElement(root, 'Arrangement', id='arrangement')
    ET.SubElement(arrangement, 'Lanes', timeUnit='beats', id='lanes')
    metadata = ET.Element('MetaData')
    ET.SubElement(metadata, 'Title').text = destination.stem
    ET.SubElement(metadata, 'Comment').text = 'Migration candidate; routing and host validation required.'
    ET.indent(root)
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('project.xml', ET.tostring(root, encoding='utf-8', xml_declaration=True))
        archive.writestr('metadata.xml', ET.tostring(metadata, encoding='utf-8', xml_declaration=True))
        for path, payload in payloads.items():
            archive.writestr(path, payload)


def inventory(library: Library, repo: Path) -> dict[str, object]:
    expected = {p.resolve() for p in (repo / 'lib/surge').rglob('*.fxp')}
    included = {s.source for s in library.sounds}
    return {'source': str(library.source), 'source_sha256': library.sha256,
            'groups': library.groups, 'count': len(library.sounds),
            'repo_fxp_count': len(expected), 'missing_repo_fxp': sorted(map(str, expected - included)),
            'sounds': [{'name': s.name, 'group': s.group, 'identity': s.identity,
                        'source': str(s.source), 'plugin': s.plugin, 'gain': s.gain,
                        'sfz': str(s.sfz) if s.sfz else None,
                        'state_sha256': hashlib.sha256(s.state).hexdigest() if s.state else None}
                       for s in library.sounds],
            'pending': ['Bitwig import/state round-trip', 'sfizz audio/CC verification',
                        'Shared MIDI routing', 'Exclusive audition/editor automation',
                        'Basic Keys ReaVerbate replacement with Bitwig Reverb (approved)',
                        'Track gains above Bitwig fader range', 'Hardware/recording/reopen checks']}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--probe', action='store_true')
    args = parser.parse_args()
    library = read_library(args.source)
    report = inventory(library, Path(__file__).resolve().parents[3])
    if report['missing_repo_fxp']:
        raise ValueError(f"Missing repository FXPs: {report['missing_repo_fxp']}")
    if args.probe:
        library = replace(library, groups=library.groups[:1], sounds=library.sounds[:4])
    write_project(library, args.destination)
    args.destination.with_suffix('.inventory.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(f'Wrote {len(library.sounds)} sounds to {args.destination}; source unchanged')


if __name__ == '__main__':
    main()
