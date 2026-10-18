"""Read-only extraction of the supported REAPER Library layout."""
from __future__ import annotations

import base64
import hashlib
import math
import re
import shlex
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Sound:
    name: str
    group: str
    identity: str
    source: Path
    gain: float
    pan: float
    plugin: str
    state: bytes
    sfz: Path | None = None
    scala: Path | None = None
    parameters: tuple[tuple[str, float], ...] = ()
    controllers: tuple[tuple[int, float], ...] = ()


@dataclass(frozen=True)
class Library:
    source: Path
    sha256: str
    master_gain: float
    tempo: float
    chord_state: bytes
    groups: tuple[tuple[str, float, float], ...]
    sounds: tuple[Sound, ...]


def field(block: str, name: str) -> tuple[str, ...]:
    matches = re.findall(r'^\s*' + re.escape(name) + r' (.+)$', block, re.M)
    if len(matches) != 1:
        raise ValueError(f'Expected one {name}, found {len(matches)}')
    return tuple(shlex.split(matches[0]))


def raw_state(block: str) -> bytes:
    states = re.findall(r'<STATE\n(.*?)\n\s*>', block, re.S)
    if len(states) != 1:
        raise ValueError('Expected exactly one plugin state')
    return base64.b64decode(''.join(states[0].split()), validate=True)


def resolve_file(value: str, project: Path) -> Path:
    path = Path(value)
    path = path if path.is_absolute() else project.parent / path
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.resolve()


def piano_state(block: str, project: Path) -> tuple[
    Path, Path, tuple[tuple[str, float], ...], tuple[tuple[int, float], ...]
]:
    sfz = resolve_file(field(block, 'P http://sfztools.github.io/sfizz:sfzfile')[0], project)
    scala = resolve_file(field(block, 'P http://sfztools.github.io/sfizz:tuningfile')[0], project)
    parameters: list[tuple[str, float]] = []
    for line in re.findall(r'^\s*P ([a-z_]+ .+)$', block, re.M):
        parts = shlex.split(line)
        if len(parts) % 2:
            raise ValueError('Invalid sfizz parameter pairs')
        parameters.extend((parts[i], float(parts[i + 1])) for i in range(0, len(parts), 2))
    controllers = tuple((int(cc), float(value)) for cc, value in re.findall(
        r'F http://sfztools.github.io/sfizz#cc(\d+) ([\d.e+-]+) 1', block))
    return sfz, scala, tuple(parameters), controllers


def read_library(project: Path) -> Library:
    data = project.read_bytes()
    text = data.decode('utf-8').replace('\r\n', '\n')
    header, *blocks = text.split('  <TRACK ')
    groups: list[tuple[str, float, float]] = []
    sounds: list[Sound] = []
    current_group = ''
    chord_states: list[bytes] = []
    for block in blocks:
        name = field(block, 'NAME')[0]
        gain, pan = (float(v) for v in field(block, 'VOLPAN')[:2])
        if not math.isfinite(gain) or gain < 0 or not -1 <= pan <= 1:
            raise ValueError(f'Invalid gain/pan: {name}')
        bus = field(block, 'ISBUS')
        if bus == ('1', '1'):
            if current_group:
                raise ValueError('Nested REAPER folders not supported by this importer')
            current_group = name
            groups.append((name, gain, pan))
        elif 'org.utrp.chordlab' in block:
            chord_states.append(raw_state(block))
        elif re.search(r'^\s*utrp_patch ', block, re.M):
            if not current_group:
                raise ValueError(f'Sound outside folder: {name}')
            identity = field(block, 'utrp_patch')[0]
            source = resolve_file(field(block, 'utrp_patch_source')[0], project)
            if 'org.surge-synth-team.surge-xt' in block:
                state = raw_state(block)
                if not state.startswith(b'sub3'):
                    raise ValueError(f'Invalid Surge state: {name}')
                sounds.append(Sound(name, current_group, identity, source, gain, pan,
                                    'org.surge-synth-team.surge-xt', state))
            elif 'http://sfztools.github.io/sfizz "' in block:
                sfz, scala, params, ccs = piano_state(block, project)
                sounds.append(Sound(name, current_group, identity, source, gain, pan,
                                    'sfizz', b'', sfz, scala, params, ccs))
            else:
                raise ValueError(f'Unsupported instrument: {name}')
        else:
            raise ValueError(f'Unaccounted track: {name}')
        if bus == ('2', '-1'):
            current_group = ''
    if current_group or len(chord_states) != 1 or not sounds:
        raise ValueError('Incomplete source library')
    if len({sound.identity for sound in sounds}) != len(sounds):
        raise ValueError('Duplicate sound identity')
    return Library(project.resolve(), hashlib.sha256(data).hexdigest(),
                   float(field(header, 'MASTER_VOLUME')[0]), float(field(header, 'TEMPO')[0]),
                   chord_states[0], tuple(groups), tuple(sounds))
