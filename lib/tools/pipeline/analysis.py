"""Analysis side of the pipeline (librosa venv): separate / scan / measure / drums.

Usage:
  python analysis.py <spec.toml> separate   # demucs -> ~/.cache/demucs-stems
  python analysis.py <spec.toml> scan       # coarse per-track spectrograms + windows
  python analysis.py <spec.toml> measure    # deep target measurements + ref cuts
  python analysis.py <spec.toml> drums      # onset/classify/one-shots/rebuild
  python analysis.py <spec.toml> all
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import librosa
import librosa.display
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
from albumspec import STEMS_DIR, AlbumSpec, load  # noqa: E402
from spectral import band_profile, hz_to_note  # noqa: E402

SCAN_SR = 22050
CLASSES = ("kick", "snare", "hat", "perc")


# ------------------------------------------------------------------ common ---
def slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower()


def out_dir(spec: AlbumSpec, kind: str) -> Path:
    d = spec.project_dir / kind
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- separate ---
def cmd_separate(spec: AlbumSpec) -> None:
    todo = [spec.flac(t) for t in
            {tg.track for tg in spec.targets} | {d.track for d in spec.drums}
            if not (STEMS_DIR / "htdemucs" / t / "other.wav").exists()]
    if not todo:
        print("stems already cached")
        return
    STEMS_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "demucs", "-n", "htdemucs", "-d", "cpu",
                    "-o", str(STEMS_DIR)] + [str(p) for p in todo], check=True)


# -------------------------------------------------------------------- scan ---
def cmd_scan(spec: AlbumSpec) -> None:
    out = out_dir(spec, "scan")
    results = []
    for flac in sorted(spec.album_dir.glob("*.flac")):
        y, sr = librosa.load(flac, sr=SCAN_SR, mono=True)
        dur = len(y) / sr
        S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
        H, P = librosa.decompose.hpss(S, margin=2.0)
        eps = 1e-10
        harm = (H ** 2).sum(axis=0)
        perc = (P ** 2).sum(axis=0)
        ratio = harm / (harm + perc + eps)
        flat = librosa.feature.spectral_flatness(S=S)[0]
        rms = librosa.feature.rms(S=S)[0]
        Hn = H / (np.linalg.norm(H, axis=0, keepdims=True) + eps)
        sustain = np.concatenate([[0.0], (Hn[:, 1:] * Hn[:, :-1]).sum(axis=0)])
        t = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=512)
        win = int(3.0 * sr / 512)
        windows = []
        for s0 in range(0, S.shape[1] - win, win // 2):
            sl = slice(s0, s0 + win)
            w_rms = float(rms[sl].mean())
            if w_rms < 1e-4:
                continue
            windows.append({
                "t0": round(float(t[s0]), 1),
                "score": round(float(ratio[sl].mean() * sustain[sl].mean()
                               * (1 - min(flat[sl].mean() * 20, 0.9))), 3),
            })
        fig, ax = plt.subplots(figsize=(16, 5), dpi=100)
        M = librosa.feature.melspectrogram(S=S ** 2, sr=sr, n_mels=256)
        librosa.display.specshow(librosa.power_to_db(M, ref=np.max), sr=sr,
                                 hop_length=512, x_axis="time", y_axis="mel",
                                 ax=ax, cmap="magma")
        ax.set_title(flac.stem)
        fig.tight_layout()
        fig.savefig(out / f"{slug(flac.stem)}.png")
        plt.close(fig)
        top = sorted(windows, key=lambda w: -w["score"])[:6]
        results.append({"track": flac.stem, "duration": round(dur, 1),
                        "top_windows": top})
        best = top[0] if top else {}
        print(f"{flac.stem[:50]:52s} best@{best.get('t0', '-'):>6} "
              f"score={best.get('score', '-')}", flush=True)
    (out / "summary.json").write_text(json.dumps(results, indent=1, default=float))


# ----------------------------------------------------------------- measure ---
def _peak_table(y: np.ndarray, sr: int, n: int = 22) -> list[dict]:
    spec = np.abs(librosa.stft(y, n_fft=8192, hop_length=2048)).mean(axis=1)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=8192)
    db = librosa.amplitude_to_db(spec, ref=spec.max())
    peaks = []
    for i in range(2, len(db) - 2):
        if db[i] > db[i - 1] and db[i] >= db[i + 1] and db[i] > -55 and freqs[i] > 25:
            a, b, c = db[i - 1], db[i], db[i + 1]
            d = 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
            peaks.append((freqs[i] + d * (freqs[1] - freqs[0]), b))
    peaks.sort(key=lambda p: -p[1])
    kept: list[tuple[float, float]] = []
    for f, a in peaks:
        if all(abs(f - kf) > 40 for kf, _ in kept):
            kept.append((f, a))
        if len(kept) >= n:
            break
    kept.sort(key=lambda p: p[0])
    return [{"hz": round(f, 1), "db": round(float(a), 1), "note": hz_to_note(f)}
            for f, a in kept]


def cmd_measure(spec: AlbumSpec) -> None:
    refs = out_dir(spec, "refs")
    results = {}
    for tg in spec.targets:
        y2, sr = sf.read(spec.stems(tg.track) / f"{tg.stem}.wav", dtype="float32")
        y2 = y2.T[:, int(tg.t0 * sr): int(tg.t1 * sr)]
        y = y2.mean(axis=0)
        peaks = _peak_table(y, sr)
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
        onset = librosa.onset.onset_detect(y=y, sr=sr, hop_length=512, backtrack=True)
        rises = []
        for o in onset:
            seg = rms[o:o + int(2.0 * sr / 512)]
            if len(seg) < 8:
                continue
            lo = np.argmax(seg > 0.1 * seg.max())
            hi = np.argmax(seg > 0.9 * seg.max())
            if hi > lo:
                rises.append((hi - lo) * 512 / sr)
        L, R = y2[0], y2[1]
        cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=2048)[0]
        results[tg.key] = {
            "track": tg.track, "t0": tg.t0, "t1": tg.t1, "stem": tg.stem,
            "peaks": peaks,
            "attack_med_ms": round(float(np.median(rises)) * 1000) if rises else None,
            "lr_corr": round(float(np.corrcoef(L, R)[0, 1]), 3),
            "centroid_med_hz": round(float(np.median(cent))),
        }
        sf.write(refs / f"{tg.key}-stem.wav", y2.T, sr)
        orig, osr = sf.read(spec.flac(tg.track), dtype="float32")
        sf.write(refs / f"{tg.key}-mix.wav", orig[int(tg.t0 * osr): int(tg.t1 * osr)], osr)
        print(f"{tg.key:24s} attack={results[tg.key]['attack_med_ms']}ms "
              f"centroid={results[tg.key]['centroid_med_hz']}Hz", flush=True)
    (spec.project_dir / "measurements.json").write_text(
        json.dumps(results, indent=1, default=float))


# ------------------------------------------------------------------- drums ---
def _classify(y: np.ndarray, sr: int) -> str:
    spec = np.abs(np.fft.rfft(y * np.hanning(len(y)))) ** 2
    freqs = np.fft.rfftfreq(len(y), 1 / sr)
    lo = spec[freqs < 130].sum()
    mid = spec[(freqs >= 200) & (freqs < 1800)].sum()
    hi = spec[freqs >= 4000].sum()
    tot = lo + mid + hi + 1e-12
    if lo / tot > 0.5:
        return "kick"
    if hi / tot > 0.6:
        return "hat"
    if mid / tot > 0.45:
        return "snare"
    return "perc"


def cmd_drums(spec: AlbumSpec) -> None:
    for seg in spec.drums:
        y2, sr = sf.read(spec.stems(seg.track) / "drums.wav", dtype="float32")
        y2 = y2[int(seg.t0 * sr): int(seg.t1 * sr)].T
        y = y2.mean(axis=0)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=256)

        M = librosa.feature.melspectrogram(y=y, sr=sr, hop_length=256, n_mels=128)
        hi_rows = librosa.mel_frequencies(128, fmax=sr / 2) > 5000
        env_full = librosa.onset.onset_strength(S=librosa.power_to_db(M), sr=sr)
        env_hi = librosa.onset.onset_strength(S=librosa.power_to_db(M[hi_rows]), sr=sr)

        def detect(env, delta):
            bt = librosa.onset.onset_detect(onset_envelope=env, sr=sr,
                                            hop_length=256, backtrack=True,
                                            delta=delta, wait=2)
            pk = librosa.onset.onset_detect(onset_envelope=env, sr=sr,
                                            hop_length=256, delta=delta, wait=2)
            t = librosa.frames_to_time(bt, sr=sr, hop_length=256)
            s = env[pk]
            n = min(len(t), len(s))
            return t[:n], s[:n]

        t_full, s_full = detect(env_full, 0.04)
        t_hi, s_hi = detect(env_hi, 0.5)
        win = int(0.08 * sr)
        hits = []
        for t, s in zip(t_full, s_full):
            i = int(t * sr)
            if i + win <= len(y):
                hits.append({"t": round(float(t), 4),
                             "cls": _classify(y[i:i + win], sr), "vel": float(s)})
        known = np.array([h["t"] for h in hits]) if hits else np.array([0.0])
        scale = (s_full.max() / (s_hi.max() + 1e-9)) if len(s_full) and len(s_hi) else 1.0
        for t, s in zip(t_hi, s_hi):
            if np.abs(known - t).min() >= 0.018:
                hits.append({"t": round(float(t), 4), "cls": "hat",
                             "vel": float(s) * scale * 0.6})
        hits.sort(key=lambda h: h["t"])
        vmax = max((h["vel"] for h in hits), default=1.0) + 1e-9
        for h in hits:
            h["vel"] = min(127, int(30 + 97 * h["vel"] / vmax))

        shots: dict[str, np.ndarray] = {}
        shot_len = int(0.30 * sr)
        for cls in CLASSES:
            cands = sorted((h for h in hits if h["cls"] == cls),
                           key=lambda h: -h["vel"])
            for h in cands:
                nxt = [x for x in hits if x["t"] > h["t"]]
                if (nxt[0]["t"] - h["t"] if nxt else 1.0) > 0.26 or h is cands[-1]:
                    i = int(h["t"] * sr)
                    cut = y2[:, i:i + shot_len].copy()
                    if cut.shape[1] < shot_len // 2:
                        continue
                    fade = np.linspace(1, 0, int(0.02 * sr))
                    cut[:, -len(fade):] *= fade
                    shots[cls] = cut
                    break

        seg_dir = out_dir(spec, f"drums/{seg.tag}")
        for cls, cut in shots.items():
            sf.write(seg_dir / f"{cls}.wav",
                     (cut * 0.891 / (np.abs(cut).max() + 1e-9)).T, sr)
        dur = seg.t1 - seg.t0
        mix = np.zeros((2, int(dur * sr) + shot_len))
        for h in hits:
            if h["cls"] not in shots:
                continue
            cut = shots[h["cls"]]
            i = int(h["t"] * sr)
            n = min(cut.shape[1], mix.shape[1] - i)
            if n > 0:
                mix[:, i:i + n] += cut[:, :n] * (h["vel"] / 127.0) ** 1.5
        sf.write(seg_dir / "rebuild.wav",
                 (mix * 0.5 / (np.abs(mix).max() + 1e-9)).T, sr)
        sf.write(seg_dir / "ref-stem.wav",
                 (y2 * 0.5 / (np.abs(y2).max() + 1e-9)).T, sr)
        meta = {"track": seg.track, "t0": seg.t0, "t1": seg.t1,
                "tempo": round(float(np.atleast_1d(tempo)[0]), 1), "hits": hits}
        (seg_dir / "pattern.json").write_text(json.dumps(meta, indent=1, default=float))
        print(f"{seg.tag:20s} tempo={meta['tempo']} hits={len(hits)} "
              f"shots={sorted(shots)}", flush=True)


def main() -> None:
    spec = load(Path(sys.argv[1]))
    cmds = {"separate": cmd_separate, "scan": cmd_scan,
            "measure": cmd_measure, "drums": cmd_drums}
    what = sys.argv[2] if len(sys.argv) > 2 else "all"
    for name in (cmds if what == "all" else {what: cmds[what]}):
        cmds[name](spec)


if __name__ == "__main__":
    main()
