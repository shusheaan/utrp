"""Reproducible full-fretboard synthetic study; never installs or touches a DAW."""
from dataclasses import dataclass, replace
from itertools import combinations
import json
from pathlib import Path
import sys
from time import perf_counter
import tomllib

import numpy as np
from numpy.typing import NDArray

from dyad_experiment import Analysis, analyze_audio, frequency


@dataclass(frozen=True)
class Study:
    frame_variants_ms: tuple[int, ...]
    holdout_cents: float
    holdout_balance: float
    holdout_noise_rms: float
    open_notes: tuple[int, ...]
    max_fret: int
    hold_ms: int
    silence_ms: int
    seed: int

    @classmethod
    def from_file(cls, path: Path) -> 'Study':
        data = tomllib.loads(path.read_text())['study']
        if set(data) != {'open_notes', 'max_fret', 'hold_ms', 'silence_ms', 'seed',
                         'frame_variants_ms', 'holdout_cents', 'holdout_balance', 'holdout_noise_rms'}:
            raise ValueError('Unexpected study settings')
        notes = data['open_notes']
        if not isinstance(notes, list) or len(notes) != 6 or any(type(n) is not int or not 24 <= n <= 84 for n in notes):
            raise ValueError('Expected six guitar open MIDI pitches')
        for key in ('max_fret', 'hold_ms', 'silence_ms', 'seed'):
            if type(data[key]) is not int:
                raise ValueError(f'Expected integer {key}')
        if not (0 <= data['max_fret'] <= 24 and 128 <= data['hold_ms'] <= 1000
                and 64 <= data['silence_ms'] <= 1000 and data['seed'] >= 0):
            raise ValueError('Study bounds')
        variants = data['frame_variants_ms']
        if not isinstance(variants, list) or not variants or any(type(v) is not int or not 32 <= v <= 128 for v in variants):
            raise ValueError('Expected frame variants in milliseconds')
        for key, lower, upper in (('holdout_cents', 0, 30), ('holdout_balance', 0.5, 1), ('holdout_noise_rms', 0, 0.01)):
            if type(data[key]) not in (int, float) or not lower <= data[key] <= upper:
                raise ValueError(f'Invalid holdout setting: {key}')
        return cls(tuple(variants), data['holdout_cents'], data['holdout_balance'], data['holdout_noise_rms'],
                   tuple(notes), data['max_fret'], data['hold_ms'], data['silence_ms'], data['seed'])


def fretboard_pairs(study: Study) -> tuple[tuple[int, int], ...]:
    # Different strings, all fret combinations. Includes non-ergonomic stretches;
    # this is a pitch-range stress test, not a fingering recommendation.
    return tuple(sorted({tuple(sorted((a + fa, b + fb)))
                         for a, b in combinations(study.open_notes, 2)
                         for fa in range(study.max_fret + 1)
                         for fb in range(study.max_fret + 1) if a + fa != b + fb}))


def synthesize(notes: tuple[int, ...], samples: int, rate: int, shape: str,
               seed: int, cents: float = 0.0, balance: float = 1.0) -> NDArray[np.float64]:
    rng = np.random.default_rng(seed)
    t = np.arange(samples, dtype=np.float64) / rate
    audio = np.zeros(samples, dtype=np.float64)
    for index, note in enumerate(notes):
        wave = np.zeros(samples, dtype=np.float64)
        for h in range(1, 13):
            if shape == 'sine' and h > 1:
                break
            weight = 1 / h ** (1.5 if shape == 'plucked' else 1.0)
            if shape == 'missing' and h == 1:
                weight = 0.0
            if shape == 'dominant' and h == 2:
                weight = 2.5
            hz = frequency(note) * 2 ** ((cents if index % 2 == 0 else -cents) / 1200) * h
            if hz >= rate / 2:
                break
            wave += weight * np.sin(2 * np.pi * hz * t + rng.uniform(-np.pi, np.pi))
        rms = float(np.sqrt(np.mean(wave * wave)))
        wave *= 0.08 / max(rms, 1e-20)
        if index:
            wave *= balance
        audio += wave
    return audio * (1 - np.exp(-t * 1000)) * np.exp(-t * 1.2)


def matrix(config: Analysis, study: Study, holdout: bool = False) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for shape in (('rich',) if holdout else ('sine', 'plucked')):
        for index, notes in enumerate(fretboard_pairs(study)):
            size = round(config.sample_rate * study.hold_ms / 1000)
            audio = synthesize(notes, size, config.sample_rate, shape, study.seed + index + (1 if holdout else 0),
                               study.holdout_cents if holdout else 0, study.holdout_balance if holdout else 1)
            if holdout:
                audio += np.random.default_rng(study.seed + index).normal(0, study.holdout_noise_rms, size)
            pad = np.zeros(round(config.sample_rate * study.silence_ms / 1000))
            frames = analyze_audio(np.concatenate((pad, audio, pad)), config)
            right = [f for f in frames if f.notes == notes and len(pad) < f.samples <= len(pad)+size]
            late_only = not right and any(f.notes == notes for f in frames)
            wrong = [f for f in frames if f.notes and f.notes != notes]
            rows.append({'shape': shape, 'expected': notes,
                         'wrong_notes': sorted({f.notes for f in wrong}),
                         'result': 'wrong' if wrong else 'correct' if right else 'late' if late_only else 'abstain',
                         'correct_frames': len(right), 'wrong_frames': len(wrong), 'late_only': late_only,
                         'first_correct_ms': (right[0].samples-len(pad))*1000/config.sample_rate if right else None,
                         'release_tail_ms': max(0, (max((f.samples for f in frames if f.notes),
                             default=len(pad)+size)-len(pad)-size)*1000/config.sample_rate)})
    return rows


def controls(config: Analysis, study: Study) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    size = config.frame_samples + config.hop_samples
    for shape in ('sine', 'plucked', 'dominant', 'missing'):
        for note in range(config.min_note, config.max_note + 1):
            signal = synthesize((note,), size, config.sample_rate, shape, study.seed + note)
            output = analyze_audio(signal, config)[-1]
            rows.append({'kind': shape, 'input': (note,), 'actual': output.notes})
    rng = np.random.default_rng(study.seed)
    for kind, audio in (('silence', np.zeros(size)), ('dc', np.full(size, 0.1)),
                        ('noise', rng.normal(0, 0.05, size)), ('nan', np.full(size, np.nan)),
                        ('clipped', np.ones(size))):
        rows.append({'kind': kind, 'input': (), 'actual': analyze_audio(audio, config)[-1].notes})
    for notes in ((50, 55, 59), (48, 52, 55), (40, 47, 52)):
        signal = synthesize(notes, size, config.sample_rate, 'plucked', study.seed)
        rows.append({'kind': 'unsupported_three', 'input': notes,
                     'actual': analyze_audio(signal, config)[-1].notes})
    return rows


def sequences(config: Analysis, study: Study) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for notes in ((50, 55), (57, 62), (40, 41), (64, 68), (76, 79), (52, 64), (52, 59)):
        length = round(config.sample_rate * study.hold_ms / 1000)
        pad = np.zeros(round(config.sample_rate * study.silence_ms / 1000))
        signal = synthesize(notes, length, config.sample_rate, 'plucked', study.seed)
        audio = np.concatenate((pad, signal, pad))
        start = len(pad)
        end = start + length
        frames = analyze_audio(audio, config)
        correct = [f for f in frames if start < f.samples <= end and f.notes == notes]
        wrong = [f for f in frames if f.notes and f.notes != notes]
        last = max((f.samples for f in frames if f.notes), default=end)
        rows.append({'notes': notes, 'first_correct_ms': (correct[0].samples-start)*1000/config.sample_rate if correct else None,
                     'wrong_frames': len(wrong), 'active_frames': sum(bool(f.notes) for f in frames),
                     'release_tail_ms': max(0, (last-end)*1000/config.sample_rate),
                     'trace': [{'ms': f.samples*1000/config.sample_rate, 'notes': f.notes, 'reason': f.reason} for f in frames]})
    return rows


def run(path: Path, destination: Path) -> None:
    config, study = Analysis.from_file(path), Study.from_file(path)
    destination.mkdir(parents=True, exist_ok=True)
    if min(study.open_notes) < config.min_note or max(study.open_notes)+study.max_fret > config.max_note:
        raise ValueError('Analysis range does not cover the configured fretboard')
    summaries: list[dict[str, object]] = []
    for frame_ms in study.frame_variants_ms:
        variant = replace(config, frame_ms=frame_ms)
        started = perf_counter()
        rows = matrix(variant, study)
        heldout = matrix(variant, study, holdout=True)
        negative = controls(variant, study)
        timing = sequences(variant, study)
        summary = {'frame_ms': frame_ms, 'pair_count': len(fretboard_pairs(study)),
                   'cases': len(rows), 'correct': sum(r['result']=='correct' for r in rows),
                   'wrong': sum(r['result']=='wrong' for r in rows),
                   'abstain': sum(r['result']=='abstain' for r in rows),
                   'late_only': sum(bool(r['late_only']) for r in rows),
                   'single_noise_false_pairs': sum(bool(r['actual']) for r in negative if r['kind'] != 'unsupported_three'),
                   'unsupported_three_emissions': sum(bool(r['actual']) for r in negative if r['kind'] == 'unsupported_three'),
                   'holdout_cases': len(heldout),
                   'holdout_correct': sum(r['result']=='correct' for r in heldout),
                   'holdout_wrong': sum(r['result']=='wrong' for r in heldout),
                   'holdout_abstain': sum(r['result']=='abstain' for r in heldout),
                   'holdout_late_only': sum(bool(r['late_only']) for r in heldout),
                   'elapsed_seconds': perf_counter()-started}
        (destination/f'{frame_ms}ms.json').write_text(json.dumps({'summary': summary, 'matrix': rows,
                                                               'holdout': heldout, 'controls': negative, 'sequences': timing}, indent=2)+'\n')
        summaries.append(summary)
        print(json.dumps(summary), flush=True)
    (destination/'summary.json').write_text(json.dumps(summaries, indent=2)+'\n')


if __name__ == '__main__':
    run(Path(sys.argv[1]), Path(sys.argv[2]))
