from dataclasses import replace
from pathlib import Path

import pytest

from lib.tools.audio_routing.policy import Config, GuitarInput, Link, Node, Port, Snapshot, guitar_commands, plan


@pytest.fixture
def config() -> Config:
    return Config.load(Path(__file__).with_name('policy.toml'))


def graph(config: Config) -> Snapshot:
    return Snapshot(
        (Node(1, '101', config.guitar.source, 'Audio/Source', 0, False),
         Node(2, '102', config.guitar.client, 'Audio/Duplex', 0, False),
         Node(3, '103', 'microphone', 'Audio/Source', 0, False),
         Node(4, '104', 'voice-recorder', 'Stream/Input/Audio', 0, False)),
        (Port(11, 1, config.guitar.source_port, 'out', 'MONO'),
         Port(21, 2, config.guitar.destination_port, 'in', ''), Port(22, 2, 'in2', 'in', ''),
         Port(31, 3, 'capture_MONO', 'out', 'MONO'), Port(41, 4, 'input', 'in', '')),
        (), '', ())


def test_input_connects_even_without_output_sink(config: Config) -> None:
    assert plan(graph(config), config) == (('pw-link', '11', '21'),)


def test_correct_input_is_idempotent(config: Config) -> None:
    state = replace(graph(config), links=(Link(100, 1, 2, 11, 21),))
    assert guitar_commands(state, config.guitar) == ()


def test_wrong_input_removed_without_touching_other_inputs(config: Config) -> None:
    state = replace(graph(config), links=(Link(100, 3, 2, 31, 21),
                                         Link(101, 3, 2, 31, 22), Link(102, 3, 4, 31, 41)))
    assert plan(state, config) == (('pw-link', '-d', '100'), ('pw-link', '11', '21'))


@pytest.mark.parametrize('missing', ['source', 'port', 'wrong_kind', 'wrong_direction', 'wrong_name'])
def test_missing_capture_never_falls_back_to_microphone(config: Config, missing: str) -> None:
    state = replace(graph(config), links=(Link(100, 3, 2, 31, 21),))
    if missing == 'source':
        state = replace(state, nodes=state.nodes[1:])
    elif missing == 'port':
        state = replace(state, ports=state.ports[1:])
    elif missing == 'wrong_kind':
        state = replace(state, nodes=(replace(state.nodes[0], kind='Audio/Sink'), *state.nodes[1:]))
    else:
        port = replace(state.ports[0], **({'direction': 'in'} if missing == 'wrong_direction'
                                         else {'name': 'monitor_MONO'}))
        state = replace(state, ports=(port, *state.ports[1:]))
    assert guitar_commands(state, config.guitar) == (('pw-link', '-d', '100'),)


def test_hotplug_rebinds_new_ids(config: Config) -> None:
    state = graph(config)
    state = replace(state, nodes=(replace(state.nodes[0], id=10, serial='new'), *state.nodes[1:]),
                    ports=(replace(state.ports[0], id=110, node=10), *state.ports[1:]))
    assert plan(state, config) == (('pw-link', '110', '21'),)


def test_other_client_and_midi_are_not_owned(config: Config) -> None:
    state = graph(config)
    state = replace(state, nodes=tuple(replace(n, name='REAPER') if n.id == 2 else n for n in state.nodes))
    assert plan(state, config) == ()
    state = replace(graph(config), ports=tuple(replace(p, name='midi_in') if p.id == 21 else p
                                             for p in graph(config).ports))
    assert plan(state, config) == ()


@pytest.mark.parametrize('duplicate', ['node', 'port'])
def test_ambiguous_capture_fails_explicitly(config: Config, duplicate: str) -> None:
    state = graph(config)
    state = (replace(state, nodes=(*state.nodes, replace(state.nodes[0], id=100))) if duplicate == 'node'
             else replace(state, ports=(*state.ports, replace(state.ports[0], id=110))))
    with pytest.raises(ValueError, match='Ambiguous'):
        plan(state, config)


@pytest.mark.parametrize('data', [None, [], {}, {'source': '   '},
                                 {'source': 1, 'source_port': 'x', 'client': 'y', 'destination_port': 'z'}])
def test_invalid_input_config_fails_explicitly(data: object) -> None:
    with pytest.raises(ValueError):
        GuitarInput.read(data)
