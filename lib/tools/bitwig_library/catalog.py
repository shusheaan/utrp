"""Inventory saved Library sounds without loading plugins or modifying the DAW.

This is a catalog preparation tool, NOT a standalone audio host. Preset paths
refer to members of the source DAWproject; no archive member is extracted.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import xml.etree.ElementTree as ET
import zipfile


@dataclass(frozen=True)
class Device:
    format: str
    identifier: str
    name: str
    enabled: bool
    preset: str | None
    sha256: str | None


@dataclass(frozen=True)
class Route:
    name: str
    gain: float
    pan: float
    muted: bool
    devices: tuple[Device, ...]


@dataclass(frozen=True)
class Preset:
    name: str
    groups: tuple[str, ...]
    kind: str
    active: bool
    route: tuple[Route, ...]
    bitwig_dependencies: tuple[str, ...]


def policy_names(config: str, symbol: str) -> tuple[str, ...]:
    match = re.search(r'const ' + re.escape(symbol) + r'\s*=\s*(\[.*?\]);', config, re.S)
    if match is None:
        raise ValueError(f'Missing catalog policy: {symbol}')
    values = json.loads(match[1])
    if (not isinstance(values, list) or not values or
            not all(isinstance(v, str) and v for v in values)):
        raise ValueError(f'Expected nonempty sound names: {symbol}')
    if len(values) != len(set(values)):
        raise ValueError(f'Duplicate sound names: {symbol}')
    return tuple(values)


def archive_read(archive: zipfile.ZipFile, member: str) -> bytes:
    path = PurePosixPath(member)
    if not member or path.is_absolute() or '..' in path.parts or '\\' in member:
        raise ValueError(f'Unsafe archive member: {member}')
    info = archive.getinfo(member)
    # Boundary guard, not a playback parameter. Do not allocate unbounded ZIP data.
    if info.file_size > 64 * 1024 * 1024:
        raise ValueError(f'Catalog member exceeds 64 MiB: {member}')
    return archive.read(info)


def device(element: ET.Element, archive: zipfile.ZipFile) -> Device:
    if element.tag not in {'BuiltinDevice', 'ClapPlugin', 'Vst3Plugin'}:
        raise ValueError(f'Unsupported device representation: {element.tag}')
    state = element.find('State')
    preset = state.attrib['path'] if state is not None else None
    digest = hashlib.sha256(archive_read(archive, preset)).hexdigest() if preset else None
    if element.tag != 'BuiltinDevice' and not preset:
        raise ValueError(f'Missing plugin preset: {element.get("name")}')
    return Device(element.tag, element.attrib['deviceID'], element.attrib['deviceName'],
                  boolean(element.find('Enabled'), 'value', True), preset, digest)


def boolean(element: ET.Element | None, key: str, default: bool) -> bool:
    value = element.get(key) if element is not None else None
    if value is None:
        return default
    if value not in {'true', 'false'}:
        raise ValueError(f'Invalid boolean: {value}')
    return value == 'true'


def level(channel: ET.Element, tag: str, default: float) -> float:
    element = channel.find(tag)
    result = float(element.attrib['value']) if element is not None else default
    if not math.isfinite(result) or result < 0 or (tag == 'Pan' and result > 1):
        raise ValueError(f'Invalid {tag}: {result}')
    return result


def route(channel: ET.Element, channels: dict[str, tuple[str, ET.Element]],
          archive: zipfile.ZipFile) -> tuple[Route, ...]:
    rows: list[Route] = []
    seen: set[str] = set()
    while True:
        identity = channel.attrib['id']
        if identity in seen:
            raise ValueError(f'Cyclic channel routing: {identity}')
        seen.add(identity)
        name, _ = channels[identity]
        rows.append(Route(name, level(channel, 'Volume', 1.0), level(channel, 'Pan', 0.5),
                          boolean(channel.find('Mute'), 'value', False),
                          tuple(device(d, archive) for d in channel.findall('Devices/*'))))
        destination = channel.get('destination')
        if destination is None:
            break
        if destination not in channels:
            raise ValueError(f'Unknown channel destination: {destination}')
        channel = channels[destination][1]
    return tuple(rows)


def grouped_tracks(parent: ET.Element, groups: tuple[str, ...] = ()) -> tuple[
        tuple[ET.Element, tuple[str, ...]], ...]:
    rows: list[tuple[ET.Element, tuple[str, ...]]] = []
    for track in parent.findall('Track'):
        rows.append((track, groups))
        rows.extend(grouped_tracks(track, (*groups, track.attrib['name'])))
    return tuple(rows)


def read_catalog(project: Path, policy: Path) -> tuple[Preset, ...]:
    config = policy.read_text()
    piano = policy_names(config, 'UTRP_LIBRARY_SOUND_NAMES')
    guitar = policy_names(config, 'UTRP_LIBRARY_GUITAR_NAMES')
    expected = set(piano + guitar)
    if len(expected) != len(piano) + len(guitar):
        raise ValueError('Piano and guitar policies overlap')
    with zipfile.ZipFile(project) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError('Duplicate archive members')
        root = ET.fromstring(archive_read(archive, 'project.xml'))
        structure = root.find('Structure')
        if structure is None:
            raise ValueError('Missing project Structure')
        tracks = grouped_tracks(structure)
        channels: dict[str, tuple[str, ET.Element]] = {}
        for track, _ in tracks:
            channel = track.find('Channel')
            if channel is not None:
                identity = channel.attrib['id']
                if identity in channels:
                    raise ValueError(f'Duplicate channel: {identity}')
                channels[identity] = (track.attrib['name'], channel)
        presets: list[Preset] = []
        seen: set[str] = set()
        for track, groups in tracks:
            name = track.attrib['name']
            if name not in expected:
                continue
            if name in seen:
                raise ValueError(f'Ambiguous Library sound: {name}')
            seen.add(name)
            channel = track.find('Channel')
            if channel is None:
                raise ValueError(f'Missing sound channel: {name}')
            chain = route(channel, channels, archive)
            dependencies = tuple(f'{r.name}: {d.name}' for r in chain for d in r.devices
                                 if d.format == 'BuiltinDevice' and d.enabled)
            presets.append(Preset(name, groups, 'piano' if name in piano else 'guitar',
                                  boolean(track, 'loaded', True), chain, dependencies))
        if seen != expected:
            raise ValueError(f'Missing Library sounds: {sorted(expected - seen)}')
        return tuple(presets)


def document(project: Path, presets: tuple[Preset, ...]) -> dict[str, object]:
    active = {kind: [p.name for p in presets if p.kind == kind and p.active]
              for kind in ('piano', 'guitar')}
    return {'schema': 1, 'source': str(project.resolve()),
            'source_sha256': hashlib.sha256(project.read_bytes()).hexdigest(),
            'scope': 'Library configured sounds; not the global Bitwig preset browser',
            'playback_verified': False, 'active': active,
            'presets': [asdict(p) for p in presets]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--policy', type=Path, default=Path(__file__).with_name('Library.config.js'))
    args = parser.parse_args()
    data = document(args.project, read_catalog(args.project, args.policy))
    # Do not silently replace an earlier catalog or project.
    with args.output.open('x') as output:
        output.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(data['active'], ensure_ascii=False))


if __name__ == '__main__':
    main()
