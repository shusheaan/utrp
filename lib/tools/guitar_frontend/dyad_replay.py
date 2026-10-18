"""Replay an explicitly selected mono WAV interval through the offline dyad experiment."""
from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
from scipy.io import wavfile

from dyad_experiment import Analysis, analyze_audio
from dyad_study import Study


def replay(config_path: Path, source: Path, start_s: float, end_s: float, output: Path) -> None:
    config = Analysis.from_file(config_path)
    rate, raw = wavfile.read(source)
    if rate != config.sample_rate or raw.ndim != 1:
        raise ValueError('Use mono WAV at the configured sample rate; no implicit mixing or resampling')
    if not 0 <= start_s < end_s <= len(raw) / rate:
        raise ValueError('Invalid replay interval')
    audio = raw[round(start_s*rate):round(end_s*rate)].astype(np.float64)
    if raw.dtype.kind == 'i':
        audio /= float(-np.iinfo(raw.dtype).min)
    elif raw.dtype.kind != 'f':
        raise ValueError('Expected signed PCM or floating-point WAV')
    results: list[dict[str, object]] = []
    for frame_ms in Study.from_file(config_path).frame_variants_ms:
        started = perf_counter()
        frames = analyze_audio(audio, replace(config, frame_ms=frame_ms))
        active = [f for f in frames if f.notes]
        results.append({'frame_ms': frame_ms, 'frames': len(frames), 'emitted_frames': len(active),
                        'pairs': {str(k): v for k, v in Counter(f.notes for f in active).items()},
                        'reason_counts': dict(Counter(f.reason for f in frames)),
                        'compute_seconds': perf_counter()-started,
                        'emissions': [{'seconds': start_s+f.samples/rate, 'notes': f.notes} for f in active]})
    output.write_text(json.dumps({'source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                                 'start_s': start_s, 'end_s': end_s, 'results': results}, indent=2)+'\n')
    for result in results:
        print(json.dumps({k: v for k, v in result.items() if k != 'emissions'}), flush=True)


if __name__ == '__main__':
    replay(Path(sys.argv[1]), Path(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), Path(sys.argv[5]))
