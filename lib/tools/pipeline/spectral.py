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


# ------------------------------------------------- deep timbre features ------
# All pure numpy on arrays; used by measure (analysis side) and browse
# (synth side). Each maps to a synth section: envelope -> Amp EG, harmonics ->
# osc waveform, centroid trajectory -> Filter EG, mod -> LFO, stereo -> FX.

def frame_rms(y: np.ndarray, hop: int = 512, win: int = 2048) -> np.ndarray:
    n = max(1, (len(y) - win) // hop)
    return np.array([np.sqrt((y[i * hop: i * hop + win] ** 2).mean())
                     for i in range(n)])


def attack_ms(y: np.ndarray, sr: int) -> float | None:
    """10%->90% rise of the first swell (mirrors measure's per-onset median)."""
    rms = frame_rms(y)
    if not len(rms) or rms.max() <= 0:
        return None
    hi = int(np.argmax(rms > 0.9 * rms.max()))
    lo = int(np.argmax(rms[:hi + 1] > 0.1 * rms.max())) if hi else 0
    return round((hi - lo) * 512 / sr * 1000) if hi > lo else None


def centroid_track(y: np.ndarray, sr: int, hop: int = 2048) -> np.ndarray:
    win = 4096
    n = max(1, (len(y) - win) // hop)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    w = np.hanning(win)
    out = np.empty(n)
    for i in range(n):
        mag = np.abs(np.fft.rfft(y[i * hop: i * hop + win] * w))
        out[i] = (freqs * mag).sum() / (mag.sum() + 1e-12)
    return out


def centroid_stats(y: np.ndarray, sr: int) -> dict:
    c = centroid_track(y, sr)
    q = len(c) // 4
    t = np.arange(len(c)) * 2048 / sr
    slope = float(np.polyfit(t, c, 1)[0]) if len(c) > 3 else 0.0
    return {"start_hz": round(float(np.median(c[:max(q, 1)]))),
            "mid_hz": round(float(np.median(c[q:3 * q] if q else c))),
            "end_hz": round(float(np.median(c[-max(q, 1):]))),
            "slope_hz_s": round(slope, 1)}


def _dominant_mod(track: np.ndarray, fs: float,
                  lo: float = 0.3, hi: float = 12.0) -> tuple[float, float]:
    """(rate_hz, depth) of the strongest oscillation in a control track."""
    if len(track) < 16:
        return 0.0, 0.0
    k = max(3, int(round(fs)))                      # ~1 s smoothing kernel
    trend = np.convolve(track, np.ones(k) / k, mode="same")
    dev = track - trend
    spec = np.abs(np.fft.rfft(dev * np.hanning(len(dev))))
    freqs = np.fft.rfftfreq(len(dev), 1 / fs)
    band = (freqs >= lo) & (freqs <= hi)
    if not band.any() or spec[band].max() <= 0:
        return 0.0, 0.0
    i = int(np.argmax(spec * band))
    depth = float(2 * spec[i] / len(dev) / (np.abs(trend).mean() + 1e-12))
    return round(float(freqs[i]), 2), round(depth, 4)


def mod_features(y: np.ndarray, sr: int) -> dict:
    rms = frame_rms(y)
    cent = centroid_track(y, sr)
    trem_rate, trem_depth = _dominant_mod(rms, sr / 512)
    bri_rate, bri_depth = _dominant_mod(cent, sr / 2048)
    return {"trem_rate_hz": trem_rate, "trem_depth": trem_depth,
            "bright_rate_hz": bri_rate, "bright_depth": bri_depth}


def stereo_features(y2: np.ndarray, sr: int) -> dict:
    """Side/mid dB per band on a (2, n) array; ~0 dB = fully wide."""
    mid, side = (y2[0] + y2[1]) / 2, (y2[0] - y2[1]) / 2
    spec_m = np.abs(np.fft.rfft(mid)) ** 2
    spec_s = np.abs(np.fft.rfft(side)) ** 2
    freqs = np.fft.rfftfreq(len(mid), 1 / sr)
    out = {}
    for name, f0, f1 in (("lo", 60, 250), ("mid", 250, 2500), ("hi", 2500, 10000)):
        sel = (freqs >= f0) & (freqs < f1)
        ratio = spec_s[sel].sum() / (spec_m[sel].sum() + 1e-12)
        out[f"width_{name}_db"] = round(float(10 * np.log10(ratio + 1e-12)), 1)
    return out


def harmonic_features(y: np.ndarray, sr: int) -> dict | None:
    """f0 guess + odd/even balance + inharmonicity from the mean spectrum.

    Chord targets make strict f0 ill-defined; treat the lowest strong peak as
    root and read the ladder above it — good enough to pick saw vs square vs
    sine-ish sources.
    """
    n_fft = 32768
    if len(y) < n_fft:
        return None
    hop = n_fft // 2
    nfr = (len(y) - n_fft) // hop
    win = np.hanning(n_fft)
    acc = np.zeros(n_fft // 2 + 1)
    for i in range(min(nfr, 40)):
        acc += np.abs(np.fft.rfft(y[i * hop: i * hop + n_fft] * win))
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    db = 20 * np.log10(acc + 1e-12)
    db -= db.max()
    low = (freqs >= 25) & (freqs <= 1000)
    idx = np.where(low & (db > -30))[0]
    if not len(idx):
        return None
    peaks = [i for i in idx if db[i] > db[i - 1] and db[i] >= db[i + 1]]
    if not peaks:
        return None
    f0 = float(freqs[peaks[0]])
    odd = even = 0.0
    devs = []
    n_harm = 0
    for k in range(2, 17):
        target = k * f0
        if target > sr / 2 - 100:
            break
        sel = (freqs > target * 0.97) & (freqs < target * 1.03)
        if not sel.any():
            continue
        j = int(np.argmax(acc * sel))
        if db[j] > -60:
            n_harm += 1
            e = float(acc[j] ** 2)
            odd, even = (odd + e, even) if k % 2 else (odd, even + e)
            devs.append(1200 * np.log2(freqs[j] / target))
    if n_harm < 2:
        return {"f0_hz": round(f0, 1), "n_harm": n_harm}
    return {"f0_hz": round(f0, 1), "n_harm": n_harm,
            "odd_even_db": round(float(10 * np.log10((odd + 1e-18)
                                                     / (even + 1e-18))), 1),
            "inharm_cents": round(float(np.median(np.abs(devs))), 1)}
