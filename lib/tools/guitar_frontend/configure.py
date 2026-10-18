"""Validate TOML defaults before generating an offline CLAP build."""
from math import ceil, floor, isfinite
from pathlib import Path
import sys
import tomllib


def fields(group: str) -> dict[str, tuple[float, float, bool]]:
    if group == 'analysis':
        return {
            'frame_ms': (32, 128, False), 'hop_ms': (1, 32, False),
            'target_rate': (8000, 16000, False),
            'min_sample_rate': (32000, 48000, False),
            'max_sample_rate': (48000, 192000, False),
            'min_note': (24, 84, True), 'max_note': (36, 108, True),
            'lowpass_hz': (500, 6000, False),
            'retrigger_ratio': (1.1, 10, False),
            'retrigger_cooldown_ms': (40, 1000, False),
            'fundamental_power_ratio': (0.001, 0.2, False),
            'subharmonic_confidence': (0.5, 0.99, False),
            'spectral_margin': (1.05, 3, False),
            'spectral_peak_cents': (5, 50, False),
        }
    return {
        'enabled': (0, 1, True), 'gate_db': (-80, -12, False),
        'confidence': (.70, .99, False), 'stability_ms': (8, 64, False),
        'release_ms': (8, 160, False), 'velocity': (1, 127, True),
        'input_channel': (0, 1, True),
    }


def validate_analysis(values: dict[str, float]) -> None:
    v = values
    if v['min_sample_rate'] > v['max_sample_rate'] or v['min_note'] >= v['max_note']:
        raise ValueError('Reversed analysis range')
    if v['hop_ms'] >= v['frame_ms'] or v['lowpass_hz'] >= v['target_rate'] / 2:
        raise ValueError('Invalid hop or anti-alias cutoff')
    min_frequency = 440 * 2 ** ((v['min_note'] - 1 - 69) / 12)
    if v['frame_ms'] / 1000 <= 2 / min_frequency:
        raise ValueError('Frame must contain more than two lowest-note periods')
    max_frequency = 440 * 2 ** ((v['max_note'] + 1 - 69) / 12)
    if floor(v['target_rate'] / max_frequency) < 2:
        raise ValueError('Highest note needs at least two samples per period')
    # Integer decimation: the largest analysis rate occurs just below the next divisor.
    divisor = floor(v['min_sample_rate'] / v['target_rate'])
    upper_rate = v['target_rate'] * (divisor + 1) / divisor
    if ceil(upper_rate * v['frame_ms'] / 1000) > 2048:
        raise ValueError('Analysis frame exceeds detector capacity')


def generate(source: Path, destination: Path) -> None:
    config = tomllib.loads(source.read_text())
    if set(config) != {'analysis', 'parameters'}:
        raise ValueError('Expected only analysis and parameters tables')
    lines = ['#pragma once', 'namespace guitar::defaults {']
    for group in ('analysis', 'parameters'):
        values = config[group]
        schema = fields(group)
        if not isinstance(values, dict) or set(values) != set(schema):
            raise ValueError(f'Unexpected or missing fields in {group}')
        checked: dict[str, float] = {}
        for name, (minimum, maximum, integral) in schema.items():
            value = values[name]
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f'Expected numeric {group}.{name}')
            number = float(value)
            if not isfinite(number) or not minimum <= number <= maximum:
                raise ValueError(f'Out-of-range {group}.{name}')
            if integral and not number.is_integer():
                raise ValueError(f'Expected integer {group}.{name}')
            checked[name] = number
            lines.append(f'inline constexpr double {name} = {number!r};')
        if group == 'analysis':
            validate_analysis(checked)
    lines.append('}')
    destination.write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    generate(Path(sys.argv[1]), Path(sys.argv[2]))
