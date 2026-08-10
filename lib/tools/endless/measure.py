"""Deep timbre measurements on demucs 'other' stems for the 4 Endless targets.

Per target segment: harmonic peak table, spectral centroid trajectory,
attack/release envelope stats, stereo width, partial modulation (vibrato/
tremolo), zoomed spectrogram + average-spectrum PNGs, reference WAV cuts.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import librosa
import soundfile as sf

BASE = Path(__file__).parent
STEMS = BASE / "stems" / "htdemucs"
MUSIC = Path("/home/shu/storage/music/Frank Ocean/Endless")
OUT = BASE / "targets"

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


@dataclass(frozen=True)
class Target:
    key: str
    track: str
    t0: float
    t1: float


TARGETS = (
    Target("A-atyourbest-intro", "01 At Your Best (You Are Love)", 0.0, 16.0),
    Target("A-atyourbest-verse", "01 At Your Best (You Are Love)", 30.0, 60.0),
    Target("A-atyourbest-outro", "01 At Your Best (You Are Love)", 282.0, 308.0),
    Target("B-mitsubushi-chords", "19 Mitsubushi Sony", 82.0, 123.0),
    Target("B-mitsubushi-filtered", "19 Mitsubushi Sony", 125.0, 160.0),
    Target("C-impietas-drone", "15 Impietas + Deathwish", 3.0, 35.0),
    Target("D-hublots-lead", "10 Hublots", 20.0, 80.0),
)


def hz_to_note(f: float) -> str:
    if f <= 0:
        return "-"
    midi = 69 + 12 * np.log2(f / 440.0)
    m = int(round(midi))
    cents = int(round((midi - m) * 100))
    return f"{NOTE_NAMES[m % 12]}{m // 12 - 1}{cents:+d}c"


def peak_table(y: np.ndarray, sr: int, n: int = 22) -> list[dict]:
    spec = np.abs(librosa.stft(y, n_fft=8192, hop_length=2048)).mean(axis=1)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=8192)
    db = librosa.amplitude_to_db(spec, ref=spec.max())
    peaks = []
    for i in range(2, len(db) - 2):
        if db[i] > db[i - 1] and db[i] >= db[i + 1] and db[i] > -55 and freqs[i] > 25:
            # parabolic interpolation
            a, b, c = db[i - 1], db[i], db[i + 1]
            d = 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
            peaks.append((freqs[i] + d * (freqs[1] - freqs[0]), b))
    # keep local maxima that dominate their 60 Hz neighbourhood
    peaks.sort(key=lambda p: -p[1])
    kept: list[tuple[float, float]] = []
    for f, a in peaks:
        if all(abs(f - kf) > 40 for kf, _ in kept):
            kept.append((f, a))
        if len(kept) >= n:
            break
    kept.sort(key=lambda p: p[0])
    return [{"hz": round(f, 1), "db": round(a, 1), "note": hz_to_note(f)} for f, a in kept]


def envelope_stats(y: np.ndarray, sr: int) -> dict:
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    t = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)
    onset = librosa.onset.onset_detect(y=y, sr=sr, hop_length=512, backtrack=True)
    rises = []
    for o in onset:
        seg = rms[o:o + int(2.0 * sr / 512)]
        if len(seg) < 8:
            continue
        peak = seg.max()
        lo = np.argmax(seg > 0.1 * peak)
        hi = np.argmax(seg > 0.9 * peak)
        if hi > lo:
            rises.append((hi - lo) * 512 / sr)
    return {
        "onsets_per_s": round(len(onset) / t[-1], 2) if len(t) else 0.0,
        "attack_med_ms": round(float(np.median(rises)) * 1000, 0) if rises else None,
        "rms_db_mean": round(float(20 * np.log10(rms.mean() + 1e-10)), 1),
        "rms_db_std": round(float(np.std(20 * np.log10(rms + 1e-10))), 1),
    }


def stereo_stats(y2: np.ndarray) -> dict:
    L, R = y2[0], y2[1]
    corr = float(np.corrcoef(L, R)[0, 1])
    mid = 0.5 * (L + R)
    side = 0.5 * (L - R)
    ms = 10 * np.log10((side ** 2).sum() / ((mid ** 2).sum() + 1e-12) + 1e-12)
    return {"lr_corr": round(corr, 3), "side_mid_db": round(float(ms), 1)}


def modulation_stats(y: np.ndarray, sr: int, peaks: list[dict]) -> dict:
    """Track the strongest partial under 2 kHz: vibrato + tremolo."""
    cands = [p for p in peaks if 80 < p["hz"] < 2000]
    if not cands:
        return {}
    f_target = max(cands, key=lambda p: p["db"])["hz"]
    S = np.abs(librosa.stft(y, n_fft=8192, hop_length=512))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=8192)
    band = (freqs > f_target - 40) & (freqs < f_target + 40)
    idx = np.where(band)[0]
    if len(idx) < 3:
        return {}
    sub = S[idx, :]
    kmax = sub.argmax(axis=0)
    amp = sub.max(axis=0)
    # parabolic interp per frame
    f_tr = []
    for j, k in enumerate(kmax):
        if 0 < k < len(idx) - 1:
            a, b, c = np.log(sub[k - 1, j] + 1e-12), np.log(sub[k, j] + 1e-12), np.log(sub[k + 1, j] + 1e-12)
            d = 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
            d = float(np.clip(d, -1, 1))
        else:
            d = 0.0
        f_tr.append(freqs[idx[k]] + d * (freqs[1] - freqs[0]))
    f_tr = np.array(f_tr)
    good = amp > amp.max() * 0.05
    if good.sum() < 32:
        return {}
    f_tr, amp = f_tr[good], amp[good]
    fr = sr / 512.0
    cents = 1200 * np.log2(f_tr / np.median(f_tr))
    cents -= cents.mean()
    spec_c = np.abs(np.fft.rfft(cents * np.hanning(len(cents))))
    mfreqs = np.fft.rfftfreq(len(cents), 1 / fr)
    vib_band = (mfreqs > 0.3) & (mfreqs < 12)
    vib_rate = float(mfreqs[vib_band][spec_c[vib_band].argmax()]) if vib_band.any() else 0.0
    adb = 20 * np.log10(amp / amp.max() + 1e-9)
    adb -= adb.mean()
    spec_a = np.abs(np.fft.rfft(adb * np.hanning(len(adb))))
    trem_rate = float(mfreqs[vib_band][spec_a[vib_band].argmax()]) if vib_band.any() else 0.0
    return {
        "tracked_hz": round(float(np.median(f_tr)), 1),
        "vib_rate_hz": round(vib_rate, 2),
        "vib_depth_cents_rms": round(float(np.sqrt((cents ** 2).mean())), 1),
        "trem_rate_hz": round(trem_rate, 2),
        "trem_depth_db_rms": round(float(np.sqrt((adb ** 2).mean())), 2),
    }


def centroid_trajectory(y: np.ndarray, sr: int) -> list[float]:
    c = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=2048)[0]
    step = max(1, int(sr / 2048))  # ~1 value per second
    return [round(float(v), 0) for v in c[::step]]


def plots(key: str, y: np.ndarray, sr: int, peaks: list[dict]) -> None:
    S = np.abs(librosa.stft(y[: int(20 * sr)], n_fft=4096, hop_length=1024))
    fig, ax = plt.subplots(figsize=(16, 6), dpi=100)
    librosa.display.specshow(
        librosa.amplitude_to_db(S, ref=np.max), sr=sr, hop_length=1024,
        x_axis="time", y_axis="linear", ax=ax, cmap="magma",
    )
    ax.set_ylim(0, 4000)
    ax.set_title(f"{key} (other stem, first 20s, 0-4kHz)")
    fig.tight_layout()
    fig.savefig(OUT / f"{key}-zoom.png")
    plt.close(fig)

    spec = np.abs(librosa.stft(y, n_fft=8192, hop_length=2048)).mean(axis=1)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=8192)
    db = librosa.amplitude_to_db(spec, ref=spec.max())
    fig, ax = plt.subplots(figsize=(16, 5), dpi=100)
    ax.semilogx(freqs[1:], db[1:], lw=0.8)
    for p in peaks:
        ax.annotate(p["note"], (p["hz"], p["db"]), fontsize=7, rotation=45)
    ax.set_xlim(30, 12000)
    ax.set_ylim(-70, 2)
    ax.grid(True, which="both", alpha=0.3)
    ax.set_title(f"{key} average spectrum")
    fig.tight_layout()
    fig.savefig(OUT / f"{key}-spectrum.png")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    results = {}
    for tg in TARGETS:
        stem_path = STEMS / tg.track / "other.wav"
        y2, sr = sf.read(stem_path, dtype="float32")
        y2 = y2.T[:, int(tg.t0 * sr): int(tg.t1 * sr)]
        y = y2.mean(axis=0)
        peaks = peak_table(y, sr)
        res = {
            "track": tg.track, "t0": tg.t0, "t1": tg.t1,
            "peaks": peaks,
            "envelope": envelope_stats(y, sr),
            "stereo": stereo_stats(y2),
            "modulation": modulation_stats(y, sr, peaks),
            "centroid_hz_per_s": centroid_trajectory(y, sr),
        }
        # vocals-stem energy in same window (synth vs voice question)
        v2, _ = sf.read(STEMS / tg.track / "vocals.wav", dtype="float32")
        v = v2.T[:, int(tg.t0 * sr): int(tg.t1 * sr)].mean(axis=0)
        res["vocal_vs_other_db"] = round(
            float(10 * np.log10(((v ** 2).mean() + 1e-12) / ((y ** 2).mean() + 1e-12))), 1
        )
        plots(tg.key, y, sr, peaks)
        # reference cuts: original mix + other stem
        orig, osr = sf.read(MUSIC / f"{tg.track}.flac", dtype="float32")
        sf.write(OUT / f"{tg.key}-mix.wav", orig[int(tg.t0 * osr): int(tg.t1 * osr)], osr)
        sf.write(OUT / f"{tg.key}-stem.wav", y2.T, sr)
        results[tg.key] = res
        print(f"{tg.key:24s} peaks={len(peaks):2d} voc/other={res['vocal_vs_other_db']:6.1f}dB "
              f"attack={res['envelope']['attack_med_ms']}ms lr_corr={res['stereo']['lr_corr']}", flush=True)
    (OUT / "measurements.json").write_text(json.dumps(results, indent=1, default=float))


if __name__ == "__main__":
    main()
