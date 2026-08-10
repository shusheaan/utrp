"""Song -> N signature timbre swatches, like a color palette from a photo.

Pipeline (all classic MIR, no training): onset + steady-grid segmentation ->
per-slice timbre features (MFCC + centroid + flatness + rms) -> k-means in
normalized feature space -> medoid slice per cluster, ranked by energy
coverage. Outputs per swatch: audio cut, feature card, and an HTML palette
whose colors are mapped from the features (hue<-centroid, sat<-1-flatness,
light<-energy) so the song literally becomes color blocks you can audition.

Usage (venv-analysis python):
  python palette.py <audio> [--k 6] [--out DIR] [--t0 S --t1 S]
Output default: ~/storage/daw/palette/<name>/
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path

os.environ.setdefault("NUMBA_CACHE_DIR", tempfile.gettempdir())
import librosa  # noqa: E402
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

SLICE_S = 1.2
FEAT_SR = 22050


def slices(y: np.ndarray, sr: int) -> list[int]:
    on = librosa.onset.onset_detect(y=y, sr=sr, units="samples", backtrack=True)
    grid = np.arange(0, len(y) - int(SLICE_S * sr), sr)          # steady 1 s grid
    starts = sorted(set(int(s) for s in np.concatenate([on, grid])
                        if s + SLICE_S * sr <= len(y)))
    return starts


def features(y: np.ndarray, sr: int, starts: list[int]) -> np.ndarray:
    rows = []
    n = int(SLICE_S * sr)
    for s in starts:
        seg = y[s:s + n]
        mfcc = librosa.feature.mfcc(y=seg, sr=sr, n_mfcc=13).mean(axis=1)
        cent = float(np.median(librosa.feature.spectral_centroid(y=seg, sr=sr)))
        flat = float(np.median(librosa.feature.spectral_flatness(y=seg)))
        rms = float(np.sqrt((seg ** 2).mean()))
        rows.append(np.concatenate([mfcc, [np.log(cent + 1), flat, rms]]))
    return np.array(rows)


def kmeans(x: np.ndarray, k: int, rng: np.random.Generator,
           iters: int = 60) -> np.ndarray:
    c = x[rng.choice(len(x), k, replace=False)]
    for _ in range(iters):
        d = ((x[:, None, :] - c[None]) ** 2).sum(axis=2)
        lab = d.argmin(axis=1)
        for j in range(k):
            if (lab == j).any():
                c[j] = x[lab == j].mean(axis=0)
    return lab


def swatch_color(cent_hz: float, flat: float, energy: float) -> str:
    hue = 260 - 220 * min(max((np.log(cent_hz) - np.log(200))
                              / (np.log(6000) - np.log(200)), 0), 1)
    sat = int(30 + 60 * (1 - min(flat * 20, 1)))
    lig = int(30 + 35 * energy)
    return f"hsl({hue:.0f},{sat}%,{lig}%)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--out", default=None)
    ap.add_argument("--t0", type=float, default=0.0)
    ap.add_argument("--t1", type=float, default=None)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    src = Path(args.audio)
    raw, sr_raw = sf.read(src, dtype="float32", always_2d=True)
    t1 = args.t1 if args.t1 else len(raw) / sr_raw
    raw = raw[int(args.t0 * sr_raw): int(t1 * sr_raw)]
    y = librosa.resample(raw.mean(axis=1), orig_sr=sr_raw, target_sr=FEAT_SR)

    starts = slices(y, FEAT_SR)
    x = features(y, FEAT_SR, starts)
    keep = x[:, -1] > 0.05 * x[:, -1].max()          # drop near-silence
    starts, x = [s for s, k_ in zip(starts, keep) if k_], x[keep]
    if len(x) < args.k:
        raise SystemExit(f"only {len(x)} usable slices; lower --k")
    z = (x - x.mean(axis=0)) / (x.std(axis=0) + 1e-9)
    lab = kmeans(z, args.k, np.random.default_rng(args.seed))

    name = re.sub(r"[^A-Za-z0-9]+", "-", src.stem).strip("-").lower()
    out = Path(args.out) if args.out else \
        Path.home() / "storage/daw/palette" / name
    out.mkdir(parents=True, exist_ok=True)

    order = sorted(range(args.k),
                   key=lambda j: -float(x[lab == j][:, -1].sum()))
    cards, total = [], float(x[:, -1].sum())
    for rank, j in enumerate(order, 1):
        mem = np.where(lab == j)[0]
        medoid = mem[((z[mem] - z[mem].mean(axis=0)) ** 2).sum(axis=1).argmin()]
        s_raw = int(starts[medoid] / FEAT_SR * sr_raw)
        cut = raw[s_raw: s_raw + int(SLICE_S * sr_raw)].copy()
        fade = np.linspace(0, 1, int(0.01 * sr_raw))[:, None]
        cut[:len(fade)] *= fade
        cut[-len(fade):] *= fade[::-1]
        sf.write(out / f"swatch-{rank}.wav", cut, sr_raw)
        cent = float(np.exp(x[medoid][-3]) - 1)
        card = {
            "rank": rank, "n_slices": int(len(mem)),
            "coverage_pct": round(100 * float(x[mem][:, -1].sum()) / total, 1),
            "t_medoid_s": round(starts[medoid] / FEAT_SR + args.t0, 2),
            "centroid_hz": round(cent),
            "flatness": round(float(x[medoid][-2]), 4),
            "color": swatch_color(cent, float(x[medoid][-2]),
                                  float(x[medoid][-1] / x[:, -1].max())),
        }
        cards.append(card)
        print(f"swatch {rank}: {card['coverage_pct']:5.1f}%  "
              f"centroid {card['centroid_hz']:5d}Hz  @{card['t_medoid_s']}s")

    (out / "palette.json").write_text(json.dumps(
        {"source": str(src), "t0": args.t0, "t1": round(t1, 1),
         "swatches": cards}, indent=1))
    blocks = "\n".join(
        f'<div class="s"><div class="b" style="background:{c["color"]}"></div>'
        f'<div class="m">#{c["rank"]} · {c["coverage_pct"]}% · '
        f'{c["centroid_hz"]}Hz · @{c["t_medoid_s"]}s<br>'
        f'<audio controls src="swatch-{c["rank"]}.wav"></audio></div></div>'
        for c in cards)
    (out / "palette.html").write_text(
        f'<!doctype html><meta charset="utf-8"><title>{name}</title><style>'
        'body{background:#16151b;color:#ddd;font:13px monospace;padding:2em}'
        '.s{display:inline-block;margin:8px;vertical-align:top}'
        '.b{width:180px;height:110px;border-radius:6px}'
        '.m{margin-top:6px}audio{width:180px;height:24px}</style>'
        f"<h2>{name} — timbre palette</h2>\n{blocks}")
    print(f"-> {out}/palette.html (+ {args.k} wav swatches)")


if __name__ == "__main__":
    main()
