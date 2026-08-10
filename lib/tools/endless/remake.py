"""Mitsubushi Sony house-section remake + same-style sketch.

Renders (surgepy, .venv314):
  remake-chords.wav  - detected progression, B3-anthemish patch, 8th pumping
  remake-bass.wav    - extracted bass line, init-based saw bass
  sketch-drums.wav   - mutated mitsu-house pattern with the sampled one-shots
  sketch-chords.wav  - new progression in the same key language
  sketch-bass.wav    - root 8th bounce
Then writes mitsu-remake.rpp.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import surgepy

sys.path.insert(0, str(Path(__file__).parent))
from render import render, walk_params, set_by_display, NoteEv  # noqa: E402

BASE = Path(__file__).parent
PROJ = Path.home() / "storage/daw/endless-ref"
OUT = PROJ / "remake"
SR = 48000
SKEL = json.loads((BASE / "mitsu-skeleton.json").read_text())

NOTE_PC = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6,
           "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
QUAL_IV = {"": (0, 4, 7), "m": (0, 3, 7), "7": (0, 4, 7, 10),
           "m7": (0, 3, 7, 10), "maj7": (0, 4, 7, 11)}


def parse_chord(name: str) -> list[int]:
    root = name[:2] if len(name) > 1 and name[1] == "#" else name[0]
    qual = name[len(root):]
    pc = NOTE_PC[root]
    r = 40 + ((pc - 4) % 12)          # root in E2..D#3
    ivs = QUAL_IV[qual]
    third = ivs[1]
    seventh = ivs[3] if len(ivs) > 3 else 12
    return [r, r + 7, r + seventh, r + 12 + third, r + 12, r + 19]


def chord_pulses(chords: list[dict], beats: list[float]) -> list[NoteEv]:
    """8th-note pumping chords following the beat grid."""
    evs = []
    half_beats = []
    for i in range(len(beats) - 1):
        half_beats += [beats[i], (beats[i] + beats[i + 1]) / 2]
    for c in chords:
        notes = parse_chord(c["chord"])
        for hb in half_beats:
            if c["t"] <= hb < c["t"] + c["dur"]:
                evs += [NoteEv(hb, n, 104, 0.17) for n in notes]
    return evs


def render_patch(patch_path: str, tweaks, phrase, dur, out, gain_db=-6.0):
    s = surgepy.createSurge(SR)
    if patch_path:
        s.loadPatch(patch_path)
    params: dict = {}
    walk_params(s.getPatch(), params)
    for substr, disp in tweaks:
        hits = [k for k in params if substr in k and k.startswith("A ")]
        hits = hits or [k for k in params if substr in k]
        if hits:
            set_by_display(s, params[hits[0]], disp)
    y = render(s, phrase, dur)
    peak = np.abs(y).max() + 1e-9
    y = y * (10 ** (gain_db / 20) / peak)
    sf.write(out, y, SR)
    print(f"{out.name:20s} {dur:5.1f}s peak->{gain_db}dB", flush=True)


def sketch_pattern(rng: np.random.Generator, bars: int, tempo: float) -> list[dict]:
    """Mutate the detected mitsu-house pattern into a new loop."""
    meta = json.loads((PROJ / "drums/mitsu-house/pattern.json").read_text())
    spb = 60.0 / tempo
    bar_len = 4 * spb
    # source micro-groove: hits from bars 4..8 of the detection
    src = [h for h in meta["hits"] if 4 * bar_len <= h["t"] < 8 * bar_len]
    hits = []
    for bar in range(bars):
        for h in src:
            t = h["t"] - 4 * bar_len + bar * bar_len
            keep = rng.random()
            if h["cls"] == "hat" and keep < 0.12:
                continue
            if h["cls"] == "kick" and keep < 0.05:
                continue
            vel = int(np.clip(h["vel"] * rng.uniform(0.85, 1.1), 25, 127))
            hits.append({"t": round(t, 4), "cls": h["cls"], "vel": vel})
        if rng.random() < 0.5:  # occasional extra offbeat kick
            hits.append({"t": round(bar * bar_len + 2.5 * spb, 4),
                         "cls": "kick", "vel": 96})
    hits.sort(key=lambda h: h["t"])
    return hits


def render_drums(hits: list[dict], dur: float, kit_dir: Path, out: Path) -> None:
    shots = {}
    for f in kit_dir.glob("*.wav"):
        if f.stem in ("kick", "snare", "hat", "perc"):
            y, sr = sf.read(f, dtype="float32")
            shots[f.stem] = (y.T, sr)
    sr = next(iter(shots.values()))[1]
    mix = np.zeros((2, int(dur * sr) + sr))
    for h in hits:
        if h["cls"] not in shots:
            continue
        cut, _ = shots[h["cls"]]
        i = int(h["t"] * sr)
        g = (h["vel"] / 127.0) ** 1.5
        n = min(cut.shape[1], mix.shape[1] - i)
        if n > 0:
            mix[:, i:i + n] += cut[:, :n] * g
    peak = np.abs(mix).max() + 1e-9
    sf.write(out, (mix * 10 ** (-6 / 20) / peak).T, sr)
    print(f"{out.name:20s} {dur:5.1f}s {len(hits)} hits", flush=True)


def wave_item(pos, length, name, file):
    return (f'    <ITEM\n      POSITION {pos}\n      LENGTH {length}\n'
            f'      NAME "{name}"\n      <SOURCE WAVE\n        FILE "{file}"\n      >\n    >\n')


def track(name, muted, items):
    return f'  <TRACK\n    NAME "{name}"\n    MUTESOLO {muted} 0 0\n{items}  >\n'


def main() -> None:
    OUT.mkdir(exist_ok=True)
    tempo = SKEL["tempo"]
    beats = SKEL["beats"]
    dur = SKEL["t1"] - SKEL["t0"]

    b3 = str(BASE / "patches/B3-anthemish.fxp")
    render_patch(b3, (("Amp EG Attack", "5.0 ms"), ("Amp EG Release", "0.30 s")),
                 chord_pulses(SKEL["chords"], beats), dur, OUT / "remake-chords.wav")

    bass_phrase = [NoteEv(b["t"], b["note"], 108, max(0.15, b["dur"] * 0.9))
                   for b in SKEL["bass"] if b["note"]]
    render_patch(None, (("Filter 1 Cutoff", "380.0 Hz"),
                        ("Amp EG Attack", "3.0 ms"), ("Amp EG Release", "0.18 s")),
                 bass_phrase, dur, OUT / "remake-bass.wav", gain_db=-8.0)

    # ---- sketch: 16 bars, new progression in the same language ----
    rng = np.random.default_rng(19)
    spb = 60.0 / tempo
    bar = 4 * spb
    sk_dur = 16 * bar + 2
    prog = ["Emaj7", "G#m7", "Amaj7", "F#7", "Emaj7", "C#m7", "Amaj7", "B7"] * 2
    sk_chords = [{"t": i * bar, "dur": bar, "chord": c} for i, c in enumerate(prog)]
    sk_beats = [i * spb for i in range(16 * 4 + 1)]
    render_patch(b3, (("Amp EG Attack", "5.0 ms"), ("Amp EG Release", "0.30 s")),
                 chord_pulses(sk_chords, sk_beats), sk_dur, OUT / "sketch-chords.wav")

    sk_bass = []
    for i, c in enumerate(prog):
        r = parse_chord(c)[0] - 12
        for k in range(8):
            note = r + (12 if k % 4 == 3 else 0)
            sk_bass.append(NoteEv(i * bar + k * spb / 2, note, 106, 0.20))
    render_patch(None, (("Filter 1 Cutoff", "380.0 Hz"),
                        ("Amp EG Attack", "3.0 ms"), ("Amp EG Release", "0.18 s")),
                 sk_bass, sk_dur, OUT / "sketch-bass.wav", gain_db=-8.0)

    render_drums(sketch_pattern(rng, 16, tempo), sk_dur,
                 PROJ / "drums/mitsu-house", OUT / "sketch-drums.wav")

    # ---- project ----
    sk0 = dur + 8.0
    tracks = [
        track("== REMAKE · REF mix 1:22-2:04", 0,
              wave_item(0, dur, "ref", "refs/B-mitsubushi-chords-mix.wav")),
        track("   REMAKE · drums (sampled rebuild)", 1,
              wave_item(0, dur, "drums", "drums/mitsu-house/rebuild.wav")),
        track("   REMAKE · chords (B3 + detected progression)", 1,
              wave_item(0, dur, "chords", "remake/remake-chords.wav")),
        track("   REMAKE · bass (pyin line)", 1,
              wave_item(0, dur, "bass", "remake/remake-bass.wav")),
        track(f"== SKETCH · new track in style ({tempo}bpm E)", 1,
              wave_item(sk0, sk_dur, "sk-drums", "remake/sketch-drums.wav")),
        track("   SKETCH · chords", 1,
              wave_item(sk0, sk_dur, "sk-chords", "remake/sketch-chords.wav")),
        track("   SKETCH · bass", 1,
              wave_item(sk0, sk_dur, "sk-bass", "remake/sketch-bass.wav")),
    ]
    rpp = ('<REAPER_PROJECT 0.1 "7.78/linux-x86_64" 1754700002\n'
           f"  TEMPO {tempo} 4 4\n" + "".join(tracks) + ">\n")
    (PROJ / "mitsu-remake.rpp").write_text(rpp)
    print(f"wrote {PROJ / 'mitsu-remake.rpp'}")


if __name__ == "__main__":
    main()
