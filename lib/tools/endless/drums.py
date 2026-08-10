"""Drum reconstruction pipeline for Endless drum stems.

Per track segment: onset detection -> hit classification (kick/snare/hat/perc)
-> exemplar one-shot extraction from the stem itself -> pattern JSON ->
numpy re-render of the pattern with the extracted one-shots (A/B against stem).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import librosa
import soundfile as sf

BASE = Path(__file__).parent
STEMS = BASE / "stems" / "htdemucs"
OUT = Path.home() / "storage/daw/endless-ref/drums"

SR = 44100
CLASSES = ("kick", "snare", "hat", "perc")
GM_NOTE = {"kick": 36, "snare": 38, "hat": 42, "perc": 39}


def band_energies(y: np.ndarray, sr: int) -> tuple[float, float, float]:
    spec = np.abs(np.fft.rfft(y * np.hanning(len(y)))) ** 2
    freqs = np.fft.rfftfreq(len(y), 1 / sr)
    low = spec[freqs < 130].sum()
    mid = spec[(freqs >= 200) & (freqs < 1800)].sum()
    high = spec[freqs >= 4000].sum()
    return float(low), float(mid), float(high)


def classify(y: np.ndarray, sr: int) -> str:
    lo, mid, hi = band_energies(y, sr)
    tot = lo + mid + hi + 1e-12
    lo, mid, hi = lo / tot, mid / tot, hi / tot
    if lo > 0.5:
        return "kick"
    if hi > 0.6:
        return "hat"
    if mid > 0.45:
        return "snare"
    return "perc"


def analyze_segment(track: str, t0: float, t1: float, tag: str) -> dict:
    path = STEMS / track / "drums.wav"
    y2, sr = sf.read(path, dtype="float32")
    y2 = y2[int(t0 * sr): int(t1 * sr)].T
    y = y2.mean(axis=0)

    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=256)

    def detect(sig_env, delta):
        on_bt = librosa.onset.onset_detect(
            onset_envelope=sig_env, sr=sr, hop_length=256, backtrack=True,
            delta=delta, wait=2)
        on_pk = librosa.onset.onset_detect(
            onset_envelope=sig_env, sr=sr, hop_length=256, backtrack=False,
            delta=delta, wait=2)
        t = librosa.frames_to_time(on_bt, sr=sr, hop_length=256)
        s = sig_env[on_pk]
        n = min(len(t), len(s))
        return t[:n], s[:n]

    # full-band pass (kick/snare/perc) + dedicated high-band pass for hats,
    # so quiet 16th hats survive next to loud kicks
    M = librosa.feature.melspectrogram(y=y, sr=sr, hop_length=256, n_mels=128,
                                       fmax=sr / 2)
    hi_rows = librosa.mel_frequencies(128, fmax=sr / 2) > 5000
    env_full = librosa.onset.onset_strength(S=librosa.power_to_db(M), sr=sr)
    env_hi = librosa.onset.onset_strength(S=librosa.power_to_db(M[hi_rows]), sr=sr)
    t_full, s_full = detect(env_full, delta=0.04)
    t_hi, s_hi = detect(env_hi, delta=0.5)

    win = int(0.08 * sr)
    hits = []
    for t, s in zip(t_full, s_full):
        i = int(t * sr)
        if i + win > len(y):
            continue
        hits.append({"t": round(float(t), 4), "cls": classify(y[i:i + win], sr),
                     "vel": float(s)})
    known = np.array([h["t"] for h in hits]) if hits else np.array([0.0])
    hi_scale = (s_full.max() / (s_hi.max() + 1e-9)) if len(s_full) and len(s_hi) else 1.0
    for t, s in zip(t_hi, s_hi):
        if np.abs(known - t).min() < 0.018:
            continue  # already caught by the full-band pass
        hits.append({"t": round(float(t), 4), "cls": "hat", "vel": float(s) * hi_scale * 0.6})
    hits.sort(key=lambda h: h["t"])
    if not hits:
        return {}
    vmax = max(h["vel"] for h in hits) + 1e-9
    for h in hits:
        h["vel"] = round(min(127, int(30 + 97 * h["vel"] / vmax)), 0)

    # exemplar per class: strongest hit with no neighbour within 260 ms after it
    shots: dict[str, np.ndarray] = {}
    shot_len = int(0.30 * sr)
    for cls in CLASSES:
        cands = [h for h in hits if h["cls"] == cls]
        cands.sort(key=lambda h: -h["vel"])
        for h in cands:
            nxt = [x for x in hits if x["t"] > h["t"]]
            gap = (nxt[0]["t"] - h["t"]) if nxt else 1.0
            if gap > 0.26 or h is cands[-1]:
                i = int(h["t"] * sr)
                cut = y2[:, i:i + shot_len].copy()
                if cut.shape[1] < shot_len // 2:
                    continue
                fade = np.linspace(1, 0, int(0.02 * sr))
                cut[:, -len(fade):] *= fade
                cut[:, :int(0.002 * sr)] *= np.linspace(0, 1, int(0.002 * sr))
                shots[cls] = cut
                break

    seg_dir = OUT / tag
    seg_dir.mkdir(parents=True, exist_ok=True)
    for cls, cut in shots.items():
        peak = np.abs(cut).max() + 1e-9
        sf.write(seg_dir / f"{cls}.wav", (cut * 0.891 / peak).T, sr)

    # re-render pattern with extracted shots at original (non-quantised) times
    dur = t1 - t0
    mix = np.zeros((2, int(dur * sr) + shot_len))
    for h in hits:
        cls = h["cls"]
        if cls not in shots:
            continue
        i = int(h["t"] * sr)
        g = (h["vel"] / 127.0) ** 1.5
        cut = shots[cls]
        mix[:, i:i + cut.shape[1]] += cut * g
    peak = np.abs(mix).max() + 1e-9
    sf.write(seg_dir / "rebuild.wav", (mix * 0.5 / peak).T, sr)
    # reference cut alongside
    peak = np.abs(y2).max() + 1e-9
    sf.write(seg_dir / "ref-stem.wav", (y2 * 0.5 / peak).T, sr)

    counts = {c: sum(1 for h in hits if h["cls"] == c) for c in CLASSES}
    meta = {"track": track, "t0": t0, "t1": t1, "tempo": round(float(np.atleast_1d(tempo)[0]), 1),
            "hits": hits, "counts": counts, "shots": sorted(shots)}
    (seg_dir / "pattern.json").write_text(json.dumps(meta, indent=1, default=float))
    print(f"{tag:24s} tempo={meta['tempo']:6.1f} hits={len(hits):4d} {counts} shots={sorted(shots)}",
          flush=True)
    return meta


SEGMENTS = [
    ("19 Mitsubushi Sony", 0.0, 60.0, "mitsu-funk"),
    ("19 Mitsubushi Sony", 82.0, 124.0, "mitsu-house"),
    ("04 Unity", 0.0, 60.0, "unity"),
    ("06 Comme Des Garçons", 0.0, 56.0, "cdg"),
    ("13 Sideways", 20.0, 80.0, "sideways"),
    ("12 Slide on Me", 40.0, 100.0, "slideonme"),
]

if __name__ == "__main__":
    extra = sys.argv[1:] if len(sys.argv) > 1 else []
    segs = SEGMENTS if not extra else [
        (extra[0], float(extra[1]), float(extra[2]), extra[3])]
    for track, t0, t1, tag in segs:
        analyze_segment(track, t0, t1, tag)
