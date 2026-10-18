"""Offline mono-to-dyad false-positive screening; never connects to a host."""
from dataclasses import replace
import json
from pathlib import Path
import sys

import numpy as np
from numpy.typing import NDArray

from dyad_experiment import Analysis, analyze_audio
from dyad_study import Study, synthesize


def screen(audio: NDArray[np.float64], config: Analysis) -> dict[str, object]:
    frames = analyze_audio(audio, config)
    active = [f for f in frames if f.notes]
    return {
        'frames': len(frames), 'false_pair_frames': len(active),
        'pairs': sorted({f.notes for f in active}),
        'emissions': [{'seconds': f.samples/config.sample_rate, 'notes': f.notes}
                      for f in active],
    }


def single_attacks(config: Analysis, study: Study) -> list[dict[str, object]]:
    size = round(config.sample_rate*study.hold_ms/1000)
    pad = np.zeros(round(config.sample_rate*study.silence_ms/1000))
    rows: list[dict[str, object]] = []
    for shape in ('sine', 'plucked', 'dominant', 'missing'):
        for note in range(config.min_note, config.max_note+1):
            tone = synthesize((note,), size, config.sample_rate, shape, study.seed+note)
            rows.append({'shape': shape, 'note': note,
                         **screen(np.concatenate((pad, tone, pad)), config)})
    return rows


def melody_audio(notes: tuple[int, ...], config: Analysis, study: Study,
                 shape: str, gap_ms: int) -> NDArray[np.float64]:
    """Notes never overlap in source samples, including when gap_ms is zero."""
    size = round(config.sample_rate*study.hold_ms/1000)
    pad = np.zeros(round(config.sample_rate*study.silence_ms/1000))
    gap = np.zeros(round(config.sample_rate*gap_ms/1000))
    chunks = [pad]
    for index, note in enumerate(notes):
        chunks.extend((synthesize((note,), size, config.sample_rate, shape,
                                  study.seed+index), gap))
    return np.concatenate((*chunks, pad))


def melody_screen(config: Analysis, study: Study) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for shape in ('sine', 'plucked', 'dominant', 'missing'):
        for gap_ms in (0, study.silence_ms):
            for notes in ((50, 55, 50), (55, 50, 55), (52, 64, 52),
                          (48, 52, 55, 59, 62), (40, 41, 42, 43)):
                audio = melody_audio(notes, config, study, shape, gap_ms)
                rows.append({'notes': notes, 'shape': shape, 'gap_ms': gap_ms,
                             **screen(audio, config)})
    return rows


def run(config_path: Path, destination: Path) -> None:
    config, study = Analysis.from_file(config_path), Study.from_file(config_path)
    destination.mkdir(parents=True, exist_ok=True)
    for frame_ms in study.frame_variants_ms:
        variant = replace(config, frame_ms=frame_ms)
        singles, melodies = single_attacks(variant, study), melody_screen(variant, study)
        summary = {
            'frame_ms': frame_ms, 'hop_ms': config.hop_ms,
            'single_cases': len(singles),
            'single_false_cases': sum(bool(r['false_pair_frames']) for r in singles),
            'melody_cases': len(melodies),
            'melody_false_cases': sum(bool(r['false_pair_frames']) for r in melodies),
        }
        report = {'summary': summary, 'single_attacks': singles, 'melodies': melodies}
        (destination/f'{frame_ms}ms.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    run(Path(sys.argv[1]), Path(sys.argv[2]))
