"""Enforce one desktop output policy without restarting audio or touching inputs."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import time
import tomllib
from typing import cast

Json = None | bool | int | float | str | list['Json'] | dict[str, 'Json']
Command = tuple[str, ...]


def mapping(value: Json) -> dict[str, Json]:
    if not isinstance(value, dict):
        raise ValueError('Expected JSON object')
    return value


def sequence(value: Json) -> list[Json]:
    if not isinstance(value, list):
        raise ValueError('Expected JSON array')
    return value


@dataclass(frozen=True)
class Config:
    interval: float
    spark: str
    woo: str
    eq: str
    backend: str
    jack: tuple[tuple[str, tuple[str, ...]], ...]

    @classmethod
    def load(cls, path: Path) -> Config:
        data = tomllib.loads(path.read_text())
        names = tuple(data[k] for k in ('spark_output', 'woo_output', 'woo_eq', 'woo_backend'))
        if not all(isinstance(v, str) and v for v in names):
            raise ValueError('Output names must be nonempty strings')
        interval = float(data['poll_seconds'])
        if not 0.2 <= interval <= 30:
            raise ValueError('poll_seconds must be in 0.2..30')
        jack = data['jack_outputs']
        if not all(isinstance(v, list) and len(v) == 2 and
                   all(isinstance(p, str) and p for p in v) for v in jack.values()):
            raise ValueError('Each JACK client needs two master port names')
        return cls(interval, *names, tuple((k, tuple(v)) for k, v in jack.items()))


@dataclass(frozen=True)
class Node:
    id: int
    serial: str
    name: str
    kind: str
    priority: int
    internal: bool


@dataclass(frozen=True)
class Port:
    id: int
    node: int
    name: str
    direction: str
    channel: str


@dataclass(frozen=True)
class Link:
    id: int
    source: int
    destination: int
    source_port: int
    destination_port: int


@dataclass(frozen=True)
class Snapshot:
    nodes: tuple[Node, ...]
    ports: tuple[Port, ...]
    links: tuple[Link, ...]
    default: str
    targets: tuple[tuple[int, str], ...]

    @classmethod
    def parse(cls, text: str) -> Snapshot:
        nodes: list[Node] = []
        ports: list[Port] = []
        links: list[Link] = []
        targets: list[tuple[int, str]] = []
        default = ''
        for raw in sequence(cast(Json, json.loads(text))):
            obj = mapping(raw)
            info = mapping(obj.get('info', {}))
            props = mapping(info.get('props', {}))
            ident = int(str(obj['id']))
            kind = str(obj['type']).removeprefix('PipeWire:Interface:')
            if kind == 'Node':
                nodes.append(Node(ident, str(props['object.serial']), str(props.get('node.name', '')),
                                  str(props.get('media.class', '')), int(str(props.get('priority.session', 0))),
                                  bool(props.get('node.link-group')) or props.get('node.virtual') is True))
            elif kind == 'Port':
                ports.append(Port(ident, int(str(props['node.id'])), str(props['port.name']),
                                  str(props['port.direction']), str(props.get('audio.channel', ''))))
            elif kind == 'Link':
                links.append(Link(ident, int(str(info['output-node-id'])), int(str(info['input-node-id'])),
                                  int(str(info['output-port-id'])), int(str(info['input-port-id']))))
            elif kind == 'Metadata' and mapping(obj.get('props', {})).get('metadata.name') == 'default':
                for raw_entry in sequence(obj.get('metadata', [])):
                    entry = mapping(raw_entry)
                    if entry['key'] == 'default.audio.sink':
                        default = str(mapping(entry['value'])['name'])
                    elif entry['key'] == 'target.object':
                        targets.append((int(str(entry['subject'])), str(entry['value'])))
        return cls(tuple(nodes), tuple(ports), tuple(links), default, tuple(targets))


def choose(snapshot: Snapshot, config: Config) -> Node | None:
    sinks = {n.name: n for n in snapshot.nodes if n.kind == 'Audio/Sink'}
    if config.spark in sinks:
        return sinks[config.spark]
    if config.woo in sinks:
        return sinks.get(config.eq, sinks[config.woo])
    candidates = [n for n in sinks.values() if not n.internal and n.name != config.eq]
    return max(candidates, key=lambda n: (n.priority, n.name), default=None)


def jack_commands(snapshot: Snapshot, config: Config, target: Node) -> tuple[Command, ...]:
    commands: list[Command] = []
    sinks = {n.id for n in snapshot.nodes if n.kind == 'Audio/Sink'}
    inputs = {p.channel: p for p in snapshot.ports if p.node == target.id and p.direction == 'in'}
    if not all(ch in inputs for ch in ('FL', 'FR')):
        return ()  # Do not destroy existing routes to create an incomplete stereo pair.
    for name, names in config.jack:
        for node in (n for n in snapshot.nodes if n.name == name):
            outputs = {p.name: p for p in snapshot.ports if p.node == node.id and p.direction == 'out'}
            if not all(p in outputs for p in names):
                continue
            for port_name, channel in zip(names, ('FL', 'FR'), strict=True):
                source, dest = outputs[port_name], inputs[channel]
                for link in snapshot.links:
                    if link.source_port == source.id and link.destination in sinks and link.destination_port != dest.id:
                        commands.append(('pw-link', '-d', str(link.id)))
                if not any(l.source_port == source.id and l.destination_port == dest.id for l in snapshot.links):
                    commands.append(('pw-link', str(source.id), str(dest.id)))
    return tuple(commands)


def plan(snapshot: Snapshot, config: Config) -> tuple[Command, ...]:
    target = choose(snapshot, config)
    if target is None:
        return ()
    commands: list[Command] = []
    if snapshot.default != target.name:
        commands.append(('wpctl', 'set-default', str(target.id)))
    targets = dict(snapshot.targets)
    for node in snapshot.nodes:
        if node.kind != 'Stream/Output/Audio' or node.internal or node.name == config.backend:
            continue
        # Metadata overrides saved per-application targets for native and Pulse streams.
        if targets.get(node.id) not in (target.name, target.serial):
            commands.append(('pw-metadata', '-n', 'default', str(node.id), 'target.object', target.serial, 'Spa:Id'))
    commands.extend(jack_commands(snapshot, config, target))
    return tuple(commands)


def run(command: Command) -> str:
    return subprocess.run(command, check=True, text=True, capture_output=True, timeout=10).stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('policy.toml'))
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    config = Config.load(args.config)
    while True:
        snapshot = Snapshot.parse(run(('pw-dump',)))
        commands = plan(snapshot, config)
        for command in commands:
            print(json.dumps(command), flush=True)
            if not args.dry_run:
                run(command)
        if args.once or args.dry_run:
            return
        time.sleep(config.interval)


if __name__ == '__main__':
    main()
