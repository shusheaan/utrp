"""Coarse spectral scan of the Endless album.

For every track: log-mel spectrogram PNG + per-window features to rank
synth-pad-like segments (sustained, harmonic, low-flatness, non-percussive).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import librosa
import librosa.display

MUSIC_DIR = Path("/home/shu/storage/music/Frank Ocean/Endless")
OUT_DIR = Path(__file__).parent / "scan"
SR = 22050
WIN_S = 3.0  # analysis window in seconds


def slug(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower()
    return s


def analyze(path: Path) -> dict:
    y, sr = librosa.load(path, sr=SR, mono=True)
    dur = len(y) / sr

    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    H, P = librosa.decompose.hpss(S, margin=2.0)

    eps = 1e-10
    frame_t = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=512)
    harm_energy = (H ** 2).sum(axis=0)
    perc_energy = (P ** 2).sum(axis=0)
    total_energy = (S ** 2).sum(axis=0) + eps
    harm_ratio = harm_energy / (harm_energy + perc_energy + eps)
    flatness = librosa.feature.spectral_flatness(S=S)[0]
    rms = librosa.feature.rms(S=S)[0]

    # sustain: correlation of consecutive harmonic spectra (pads hold shape)
    Hn = H / (np.linalg.norm(H, axis=0, keepdims=True) + eps)
    sustain = np.concatenate([[0.0], (Hn[:, 1:] * Hn[:, :-1]).sum(axis=0)])

    # window aggregation
    win_frames = int(WIN_S * sr / 512)
    windows = []
    for start in range(0, S.shape[1] - win_frames, win_frames // 2):
        sl = slice(start, start + win_frames)
        w_rms = float(rms[sl].mean())
        if w_rms < 1e-4:
            continue
        windows.append({
            "t0": round(float(frame_t[start]), 1),
            "harm_ratio": round(float(harm_ratio[sl].mean()), 3),
            "flatness": round(float(flatness[sl].mean()), 4),
            "sustain": round(float(sustain[sl].mean()), 3),
            "rms_db": round(float(20 * np.log10(w_rms + eps)), 1),
        })
    # padness score: harmonic, sustained, tonal, audible
    rms_vals = np.array([w["rms_db"] for w in windows])
    rms_floor = np.percentile(rms_vals, 20) if len(rms_vals) else -80.0
    for w in windows:
        audible = 1.0 / (1.0 + np.exp(-(w["rms_db"] - rms_floor) / 3.0))
        w["score"] = round(
            w["harm_ratio"] * w["sustain"] * (1.0 - min(w["flatness"] * 20, 0.9)) * audible, 3
        )
    top = sorted(windows, key=lambda w: -w["score"])[:6]

    # spectrogram png
    fig, ax = plt.subplots(figsize=(16, 5), dpi=100)
    M = librosa.feature.melspectrogram(S=S ** 2, sr=sr, n_mels=256, fmax=SR / 2)
    librosa.display.specshow(
        librosa.power_to_db(M, ref=np.max), sr=sr, hop_length=512,
        x_axis="time", y_axis="mel", fmax=SR / 2, ax=ax, cmap="magma",
    )
    ax.set_title(path.stem)
    ax.set_xticks(np.arange(0, dur, 10))
    fig.tight_layout()
    png = OUT_DIR / f"{slug(path.stem)}.png"
    fig.savefig(png)
    plt.close(fig)

    return {"track": path.stem, "duration": round(dur, 1), "png": str(png), "top_windows": top}


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    results = []
    for path in sorted(MUSIC_DIR.glob("*.flac")):
        r = analyze(path)
        results.append(r)
        best = r["top_windows"][0] if r["top_windows"] else {}
        print(f"{r['track']:45s} {r['duration']:6.1f}s  best@{best.get('t0', '-'):>6} "
              f"score={best.get('score', '-')}", flush=True)
    (OUT_DIR / "summary.json").write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
