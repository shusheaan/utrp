"""Screen the isolated harmonic-sieve experiment; never install a plugin."""
import itertools
import json
from pathlib import Path
import sys
import tomllib

from benchmark import Fixture, audio, evaluate, evaluate_overlap, overlapping
from conservative import Config, detect


def run(analysis_path: Path, matrix_path: Path, destination: Path) -> None:
    config = Config.load(analysis_path)
    document = tomllib.loads(matrix_path.read_text())
    matrix = document['fixtures']
    if matrix['sample_rate'] != config.sample_rate:
        raise ValueError('Fixture and analyzer sample rates must match')
    results: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    overlaps: list[dict[str, object]] = []
    for section, target in (('fixtures', results), ('rejection', rejected), ('overlap', overlaps)):
        group = document[section]
        for notes, shape, level in itertools.product(group['notes'], matrix['shapes'], matrix['levels']):
            fixture = Fixture(tuple(notes), shape, level, config.sample_rate, matrix['onset_ms'],
                              matrix['sustain_ms'], matrix['silence_after_ms'], matrix['stable_ms'])
            if section == 'fixtures':
                result = evaluate(fixture, detect(audio(fixture), config))
            else:
                offsets = tuple(group['offsets_ms'][:len(notes)])
                events = detect(overlapping(fixture, offsets), config)
                result = evaluate_overlap(fixture, offsets, events)
                result['any_output'] = any(bool(n) for _, n in events)
            target.append(result)
    groups: dict[str, object] = {}
    for voices in (1, 2, 3):
        rows = [r for r in results if len(r['notes']) == voices]
        latencies = [r['first_exact_stable_ms'] for r in rows if r['first_exact_stable_ms'] is not None]
        groups[str(voices)] = {'cases': len(rows),
                              'ever_exact_20ms': len(latencies),
                              'cases_with_spurious_pitch': sum(bool(r['spurious_notes']) for r in rows),
                              'max_successful_set_latency_ms': max(latencies) if latencies else None}
    report = {'scope': 'Offline synthetic screening, not real-guitar certification or production DSP',
              'decision': 'DO NOT DEPLOY: real-guitar labels, strum rejection, latency and C++/host validation required',
              'voice_counts': groups,
              'rejection_cases': len(rejected),
              'rejection_cases_with_output': sum(bool(r['any_output']) for r in rejected),
              'overlap_cases': len(overlaps),
              'overlap_cases_with_spurious_pitch': sum(bool(r['spurious_notes']) for r in overlaps),
              'results': results, 'rejection_results': rejected, 'overlap_results': overlaps}
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if not k.endswith('results')}, indent=2))


if __name__ == '__main__':
    run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
