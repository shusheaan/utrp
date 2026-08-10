"""Extract the musical skeleton of Mitsubushi Sony 82-124s (house section):
beat grid from drums, bass line from bass stem (pyin), chords from other stem
(beat-synchronous chroma + template matching). Writes mitsu-skeleton.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import librosa
import soundfile as sf

BASE = Path(__file__).parent
STEM_DIR = BASE / "stems/htdemucs/19 Mitsubushi Sony"
T0, T1 = 82.0, 124.0

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

TEMPLATES = {}
for root in range(12):
    for qual, ivs in (("", (0, 4, 7)), ("m", (0, 3, 7)),
                      ("7", (0, 4, 7, 10)), ("m7", (0, 3, 7, 10)),
                      ("maj7", (0, 4, 7, 11))):
        v = np.zeros(12)
        for iv in ivs:
            v[(root + iv) % 12] = 1.0
        TEMPLATES[f"{NOTE_NAMES[root]}{qual}"] = v / np.linalg.norm(v)


def load(stem: str) -> tuple[np.ndarray, int]:
    y, sr = sf.read(STEM_DIR / f"{stem}.wav", dtype="float32")
    return y[int(T0 * sr): int(T1 * sr)].mean(axis=1), sr


def main() -> None:
    drums, sr = load("drums")
    tempo, beat_frames = librosa.beat.beat_track(y=drums, sr=sr, hop_length=256)
    beats = librosa.frames_to_time(beat_frames, sr=sr, hop_length=256).tolist()
    tempo = float(np.atleast_1d(tempo)[0])

    # ---- bass line ----
    bass, _ = load("bass")
    f0, voiced, _ = librosa.pyin(bass, fmin=30, fmax=350, sr=sr,
                                 frame_length=4096, hop_length=512)
    t = librosa.times_like(f0, sr=sr, hop_length=512)
    rms = librosa.feature.rms(y=bass, frame_length=4096, hop_length=512)[0]
    midi = np.where(voiced & (rms[:len(f0)] > 0.01),
                    librosa.hz_to_midi(np.nan_to_num(f0, nan=1.0)), np.nan)
    # collapse to eighth-note grid: median midi per half-beat
    half = []
    for i in range(len(beats) - 1):
        for frac in (0.0, 0.5):
            s = beats[i] + frac * (beats[i + 1] - beats[i])
            e = beats[i] + (frac + 0.5) * (beats[i + 1] - beats[i])
            sel = (t >= s) & (t < e)
            vals = midi[sel]
            vals = vals[np.isfinite(vals)]
            note = int(round(float(np.median(vals)))) if len(vals) > 4 else None
            half.append({"t": round(s, 3), "dur": round(e - s, 3), "note": note})
    # merge consecutive identical notes
    bass_notes = []
    for h in half:
        if h["note"] is None:
            continue
        if bass_notes and bass_notes[-1]["note"] == h["note"] and \
           abs(bass_notes[-1]["t"] + bass_notes[-1]["dur"] - h["t"]) < 0.02:
            bass_notes[-1]["dur"] = round(h["t"] + h["dur"] - bass_notes[-1]["t"], 3)
        else:
            bass_notes.append(dict(h))

    # ---- chords per bar (4 beats) ----
    other, _ = load("other")
    chroma = librosa.feature.chroma_cqt(y=other, sr=sr, hop_length=512)
    ct = librosa.times_like(chroma[0], sr=sr, hop_length=512)
    chords = []
    for i in range(0, len(beats) - 4, 4):
        s, e = beats[i], beats[i + 4]
        v = chroma[:, (ct >= s) & (ct < e)].mean(axis=1)
        v = v / (np.linalg.norm(v) + 1e-9)
        best = max(TEMPLATES, key=lambda k: float(v @ TEMPLATES[k]))
        chords.append({"t": round(s, 3), "dur": round(e - s, 3), "chord": best,
                       "conf": round(float(v @ TEMPLATES[best]), 3)})

    out = {"t0": T0, "t1": T1, "tempo": round(tempo, 1), "beats": [round(b, 3) for b in beats],
           "bass": bass_notes, "chords": chords}
    (BASE / "mitsu-skeleton.json").write_text(json.dumps(out, indent=1))
    print(f"tempo={tempo:.1f} beats={len(beats)} bass_notes={len(bass_notes)}")
    for c in chords[:12]:
        print(f"  bar@{c['t']:6.2f}s  {c['chord']:6s} conf={c['conf']}")
    seq = [c["chord"] for c in chords]
    print("progression:", seq)


if __name__ == "__main__":
    main()
