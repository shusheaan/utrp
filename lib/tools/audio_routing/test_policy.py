from dataclasses import replace
from itertools import permutations
from pathlib import Path
import json

import pytest

from lib.tools.audio_routing.policy import Config, Link, Node, Port, Snapshot, choose, plan


@pytest.fixture
def config() -> Config:
    return Config.load(Path(__file__).with_name('policy.toml'))


def graph(config: Config) -> Snapshot:
    nodes = (
        Node(1, '101', config.spark, 'Audio/Sink', 1000, False),
        Node(2, '102', config.woo, 'Audio/Sink', 2000, False),
        Node(3, '103', config.eq, 'Audio/Sink', 0, True),
        Node(4, '104', 'HDMI', 'Audio/Sink', 500, False),
        Node(5, '105', 'Bitwig Studio', 'Audio/Duplex', 0, False),
        Node(6, '106', 'browser', 'Stream/Output/Audio', 0, False),
        Node(7, '107', config.backend, 'Stream/Output/Audio', 0, True),
        Node(8, '108', 'recorder', 'Stream/Input/Audio', 0, False),
    )
    ports = (Port(11, 1, 'playback_FL', 'in', 'FL'), Port(12, 1, 'playback_FR', 'in', 'FR'),
             Port(21, 2, 'playback_FL', 'in', 'FL'), Port(22, 2, 'playback_FR', 'in', 'FR'),
             Port(31, 3, 'playback_FL', 'in', 'FL'), Port(32, 3, 'playback_FR', 'in', 'FR'),
             Port(51, 5, 'out1', 'out', ''), Port(52, 5, 'out2', 'out', ''),
             Port(53, 5, 'in1', 'in', ''), Port(54, 5, 'out3', 'out', ''))
    links = (Link(201, 5, 3, 51, 31), Link(202, 5, 3, 52, 32),
             Link(203, 99, 5, 99, 53), Link(204, 7, 2, 71, 21),
             Link(205, 5, 8, 51, 81), Link(206, 5, 2, 54, 21))
    return Snapshot(nodes, ports, links, config.eq, ())


@pytest.mark.parametrize('spark,woo,eq,expected', [
    (True, True, True, 1), (True, False, True, 1), (True, True, False, 1),
    (False, True, True, 3), (False, True, False, 2), (False, False, True, 4),
    (False, False, False, 4), (True, False, False, 1),
])
def test_priority(config: Config, spark: bool, woo: bool, eq: bool, expected: int) -> None:
    state = graph(config)
    omitted = {i for i, available in zip((1, 2, 3), (spark, woo, eq)) if not available}
    state = replace(state, nodes=tuple(n for n in state.nodes if n.id not in omitted))
    selected = choose(state, config)
    assert selected is not None and selected.id == expected


def test_discovery_order_does_not_change_priority(config: Config) -> None:
    state = graph(config)
    for nodes in permutations(state.nodes[:4]):
        assert choose(replace(state, nodes=nodes), config) == state.nodes[0]


def test_no_hardware_does_not_choose_dead_eq(config: Config) -> None:
    state = graph(config)
    state = replace(state, nodes=(state.nodes[2],))
    assert choose(state, config) is None
    assert plan(state, config) == ()


def test_only_master_outputs_move(config: Config) -> None:
    commands = plan(graph(config), config)
    assert commands == (
        ('wpctl', 'set-default', '1'),
        ('pw-metadata', '-n', 'default', '6', 'target.object', '101', 'Spa:Id'),
        ('pw-link', '-d', '201'), ('pw-link', '51', '11'),
        ('pw-link', '-d', '202'), ('pw-link', '52', '12'),
    )  # Capture, recorder taps, auxiliary buses and EQ backend untouched.


def test_already_correct_is_noop(config: Config) -> None:
    state = graph(config)
    state = replace(state, default=config.spark, targets=((6, '101'),),
                    links=(Link(201, 5, 1, 51, 11), Link(202, 5, 1, 52, 12)))
    assert plan(state, config) == ()


def test_hotplug_new_serial_updates_stream(config: Config) -> None:
    state = graph(config)
    state = replace(state, targets=((6, 'old-device-serial'),))
    assert ('pw-metadata', '-n', 'default', '6', 'target.object', '101', 'Spa:Id') in plan(state, config)


def test_incomplete_stereo_keeps_existing_links(config: Config) -> None:
    state = graph(config)
    state = replace(state, ports=tuple(p for p in state.ports if p.id != 12))
    assert not any(cmd[0] == 'pw-link' for cmd in plan(state, config))


def test_reaper_same_policy(config: Config) -> None:
    state = graph(config)
    state = replace(state, nodes=tuple(replace(n, name='REAPER') if n.id == 5 else n for n in state.nodes))
    assert ('pw-link', '51', '11') in plan(state, config)


def test_unknown_duplex_is_not_rewired(config: Config) -> None:
    state = graph(config)
    state = replace(state, nodes=tuple(replace(n, name='Analysis matrix') if n.id == 5 else n for n in state.nodes))
    assert not any(cmd[0] == 'pw-link' for cmd in plan(state, config))


def test_parse_metadata_and_ports() -> None:
    raw = [
        {'id': 1, 'type': 'PipeWire:Interface:Node', 'info': {'props': {
            'object.serial': 101, 'node.name': 'speaker', 'media.class': 'Audio/Sink'}}},
        {'id': 2, 'type': 'PipeWire:Interface:Metadata', 'props': {'metadata.name': 'default'},
         'metadata': [{'subject': 0, 'key': 'default.audio.sink', 'value': {'name': 'speaker'}},
                      {'subject': 5, 'key': 'target.object', 'value': 101}]},
        {'id': 3, 'type': 'PipeWire:Interface:Port', 'info': {'props': {
            'node.id': 1, 'port.name': 'playback_FL', 'port.direction': 'in', 'audio.channel': 'FL'}}},
        {'id': 4, 'type': 'PipeWire:Interface:Link', 'info': {
            'output-node-id': 5, 'input-node-id': 1, 'output-port-id': 51, 'input-port-id': 3}},
    ]
    state = Snapshot.parse(json.dumps(raw))
    assert state.default == 'speaker' and state.targets == ((5, '101'),)
    assert state.ports == (Port(3, 1, 'playback_FL', 'in', 'FL'),)
    assert state.links == (Link(4, 5, 1, 51, 3),)


@pytest.mark.parametrize('text', ['{}', '[null]', '[{"id": 1}]'])
def test_malformed_snapshot_fails_explicitly(text: str) -> None:
    with pytest.raises((ValueError, KeyError)):
        Snapshot.parse(text)
