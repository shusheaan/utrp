"""Plot band profiles: reference stem vs candidate renders, one panel per target."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf

BASE = Path(__file__).parent
RENDERS = Path.home() / "storage/daw/endless-ref/renders"

REF_SPECS = {
    "A": ("A-atyourbest-outro-stem.wav", 2.0, 22.0),
    "B": ("B-mitsubushi-chords-stem.wav", 12.0, 38.0),
    "C": ("C-impietas-drone-stem.wav", 2.0, 30.0),
    "D": ("D-hublots-lead-stem.wav", 2.0, 55.0),
}
CANDS = {
    "A": ["A1-bellpad", "A2-fmpad", "A3-mks70"],
    "B": ["B1-jupiter8", "B2-juno60", "B3-anthemish"],
    "C": ["C1-ghostpad", "C2-distant", "C3-choirpad", "C4-darkdrone"],
    "D": ["D1-suitcase", "D2-dxep", "D3-houseorgan"],
}


def band_profile(y: np.ndarray, sr: int) -> np.ndarray:
    mono = y.mean(axis=1) if y.ndim == 2 else y
    n_fft, hop = 16384, 4096
    nfr = max(1, (len(mono) - n_fft) // hop)
    win = np.hanning(n_fft)
    acc = np.zeros(n_fft // 2 + 1)
    for i in range(nfr):
        acc += np.abs(np.fft.rfft(mono[i * hop: i * hop + n_fft] * win)) ** 2
    acc /= nfr
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    edges = np.geomspace(60, 10000, 61)
    prof = np.array([
        acc[(freqs >= edges[i]) & (freqs < edges[i + 1])].mean() + 1e-12
        for i in range(60)
    ])
    bad = ~np.isfinite(prof)
    if bad.any():
        idx = np.arange(60)
        prof[bad] = np.interp(idx[bad], idx[~bad], prof[~bad])
    db = 10 * np.log10(prof)
    return db - db.max()


centers = np.geomspace(60, 10000, 61)[:-1]
fig, axes = plt.subplots(2, 2, figsize=(16, 9), dpi=100)
for ax, (tgt, (fname, t0, t1)) in zip(axes.flat, REF_SPECS.items()):
    y, sr = sf.read(BASE / "targets" / fname, dtype="float32")
    ax.plot(centers, band_profile(y[int(t0 * sr): int(t1 * sr)], sr),
            "k-", lw=2.5, label="ref stem")
    for c in CANDS[tgt]:
        y2, sr2 = sf.read(RENDERS / f"{c}.wav", dtype="float32")
        body = y2[int(1.5 * sr2): int(len(y2) - 3.0 * sr2)]
        ax.plot(centers, band_profile(body, sr2), lw=1.0, label=c)
    ax.set_xscale("log")
    ax.set_title(f"target {tgt}")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3, which="both")
fig.tight_layout()
fig.savefig(BASE / "targets/profile-compare.png")
print("saved")
