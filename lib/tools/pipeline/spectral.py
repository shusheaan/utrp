"""Pure numpy spectral helpers shared by both venv sides (no librosa, no I/O)."""
from __future__ import annotations

import numpy as np

NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def hz_to_note(f: float) -> str:
    if f <= 0:
        return "-"
    midi = 69 + 12 * np.log2(f / 440.0)
    m = int(round(midi))
    cents = int(round((midi - m) * 100))
    return f"{NOTE_NAMES[m % 12]}{m // 12 - 1}{cents:+d}c"


def band_profile(y: np.ndarray, sr: int, n_bands: int = 60,
                 fmin: float = 60.0, fmax: float = 10000.0) -> np.ndarray:
    """Mean log-power in log-spaced bands; NaN bands interpolated."""
    mono = y.mean(axis=1) if y.ndim == 2 else y
    n_fft, hop = 16384, 4096
    nfr = max(1, (len(mono) - n_fft) // hop)
    win = np.hanning(n_fft)
    acc = np.zeros(n_fft // 2 + 1)
    for i in range(nfr):
        acc += np.abs(np.fft.rfft(mono[i * hop: i * hop + n_fft] * win)) ** 2
    acc /= nfr
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    edges = np.geomspace(fmin, fmax, n_bands + 1)
    prof = np.array([
        acc[(freqs >= edges[i]) & (freqs < edges[i + 1])].mean() + 1e-12
        for i in range(n_bands)
    ])
    bad = ~np.isfinite(prof)
    if bad.any():
        idx = np.arange(n_bands)
        prof[bad] = np.interp(idx[bad], idx[~bad], prof[~bad])
    db = 10 * np.log10(prof)
    return db - db.max()


def spectral_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(((a - b) ** 2).mean()))
