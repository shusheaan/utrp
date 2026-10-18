"""Measure the unmodified upstream detector; never load it in the live DAW."""
from dataclasses import dataclass
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tomllib

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class Fixture:
    notes: tuple[int, ...]
    shape: str
    level: float
    sample_rate: int
    onset_ms: int
    sustain_ms: int
    silence_after_ms: int
    stable_ms: int


def audio(f: Fixture) -> NDArray[np.float64]:
    size = (f.onset_ms + f.sustain_ms + f.silence_after_ms) * f.sample_rate // 1000
    output = np.zeros(size, dtype=np.float64)
    time = np.arange(f.sustain_ms * f.sample_rate // 1000) / f.sample_rate
    signal = np.zeros_like(time)
    for index, note in enumerate(f.notes):
        frequency = 440 * 2 ** ((note - 69) / 12)
        for harmonic in range(1, 2 if f.shape == 'sine' else 9):
            phase = 0.13 * harmonic + index * 0.37
            signal += np.sin(2 * np.pi * frequency * harmonic * time + phase) / harmonic ** 1.4
    signal *= (1 - np.exp(-time * 1000)) * np.exp(-time * 1.8)
    peak = float(np.max(np.abs(signal)))
    start = f.onset_ms * f.sample_rate // 1000
    output[start:start + len(signal)] = signal * f.level / peak
    return output


def trace(binary: Path, samples: NDArray[np.float64]) -> tuple[tuple[float, tuple[int, ...]], ...]:
    process = subprocess.run([str(binary.resolve())], input=samples.tobytes(), capture_output=True, check=True)
    result: list[tuple[float, tuple[int, ...]]] = [(0.0, ())]
    for row in process.stdout.decode().splitlines():
        cells = row.split(',')
        result.append((float(cells[0]), tuple(int(n) for n in cells[1:])))
    return tuple(result)


def evaluate(f: Fixture, events: tuple[tuple[float, tuple[int, ...]], ...]) -> dict[str, object]:
    expected = tuple(sorted(f.notes))
    end = f.onset_ms + f.sustain_ms
    horizon = end + f.silence_after_ms
    intervals = tuple(zip(events, events[1:] + ((float(horizon), ()),)))
    correct = [(max(t, f.onset_ms), min(stop, end)) for (t, notes), (stop, _) in intervals
               if notes == expected and min(stop, end) - max(t, f.onset_ms) >= f.stable_ms]
    union = sorted({note for _, notes in events for note in notes})
    steady_total = sum(max(0.0, min(stop, end) - max(t, f.onset_ms + 100))
                       for (t, notes), (stop, _) in intervals if notes == expected)
    return {'notes': expected, 'shape': f.shape, 'peak_amplitude': f.level,
            'first_exact_stable_ms': correct[0][0] - f.onset_ms if correct else None,
            'steady_exact_fraction': steady_total / (f.sustain_ms - 100),
            'all_emitted_notes': union, 'spurious_notes': sorted(set(union) - set(expected)),
            'held_at_end': events[-1][1], 'events': events}


def overlapping(f: Fixture, offsets: tuple[int, ...]) -> NDArray[np.float64]:
    total_ms = f.onset_ms + max(offsets) + f.sustain_ms + f.silence_after_ms
    samples = np.zeros(total_ms * f.sample_rate // 1000, dtype=np.float64)
    for note, offset in zip(f.notes, offsets, strict=True):
        single = Fixture((note,), f.shape, f.level / len(f.notes), f.sample_rate,
                         f.onset_ms + offset, f.sustain_ms, f.silence_after_ms, f.stable_ms)
        component = audio(single)
        samples[:len(component)] += component
    return samples


def evaluate_overlap(f: Fixture, offsets: tuple[int, ...],
                     events: tuple[tuple[float, tuple[int, ...]], ...]) -> dict[str, object]:
    end = f.onset_ms + max(offsets) + f.sustain_ms
    current: tuple[int, ...] = ()
    index = 0
    exact = 0
    for time in range(f.onset_ms, end):
        while index + 1 < len(events) and events[index + 1][0] <= time:
            index += 1
        current = events[index][1]
        expected = tuple(sorted(n for n, offset in zip(f.notes, offsets, strict=True)
                                if f.onset_ms + offset <= time < f.onset_ms + offset + f.sustain_ms))
        exact += current == expected
    emitted = {n for _, notes in events for n in notes}
    return {'notes': f.notes, 'offsets_ms': offsets, 'shape': f.shape, 'total_peak_bound': f.level,
            'exact_time_fraction_including_transitions': exact / (end - f.onset_ms),
            'spurious_notes': sorted(emitted - set(f.notes)), 'events': events}


def main(config_path: Path, binary: Path, destination: Path) -> None:
    document = tomllib.loads(config_path.read_text())
    config = document['fixtures']
    results: list[dict[str, object]] = []
    for notes, shape, level in itertools.product(config['notes'], config['shapes'], config['levels']):
        fixture = Fixture(tuple(notes), shape, level, config['sample_rate'], config['onset_ms'],
                          config['sustain_ms'], config['silence_after_ms'], config['stable_ms'])
        results.append(evaluate(fixture, trace(binary, audio(fixture))))
    overlaps: list[dict[str, object]] = []
    offsets = tuple(document['overlap']['offsets_ms'])
    for notes, shape, level in itertools.product(document['overlap']['notes'], config['shapes'], config['levels']):
        fixture = Fixture(tuple(notes), shape, level, config['sample_rate'], config['onset_ms'],
                          config['sustain_ms'], config['silence_after_ms'], config['stable_ms'])
        overlaps.append(evaluate_overlap(fixture, offsets, trace(binary, overlapping(fixture, offsets))))
    report = {'upstream_commit': 'dc4565b3827afd34db47d8ecc770a29b1aed61f0',
              'scope': 'synthetic screening; algorithm unchanged, logging disabled, 48 kHz build',
              'cases': len(results),
              'cases_with_any_spurious_note': sum(bool(r['spurious_notes']) for r in results),
              'cases_ever_exact_for_20ms': sum(r['first_exact_stable_ms'] is not None for r in results),
              'overlap_cases': len(overlaps), 'overlaps': overlaps, 'results': results}
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('results', 'overlaps')}, indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
