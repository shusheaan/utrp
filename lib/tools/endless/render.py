"""Render Surge XT candidate patches for the Endless targets and score them
against the demucs stem references by log-band spectral distance.

Runs under .venv314 (surgepy). Pure numpy scoring - no librosa here.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import soundfile as sf
import surgepy

SR = 48000
BASE = Path(__file__).parent
FACTORY = Path("/usr/share/surge-xt/patches_factory")
REFS = BASE / "targets"
OUT_WAV = Path.home() / "storage/daw/endless-ref/renders"
OUT_FXP = BASE / "patches"


# ---------------------------------------------------------------- phrases ---
@dataclass(frozen=True)
class NoteEv:
    t: float
    note: int
    vel: int
    dur: float


def hold(notes: list[int], t0: float, dur: float, vel: int) -> list[NoteEv]:
    return [NoteEv(t0, n, vel, dur) for n in notes]


def pulses(notes: list[int], t0: float, until: float, period: float, gate: float,
           vel: int) -> list[NoteEv]:
    evs = []
    t = t0
    while t < until:
        evs.extend(NoteEv(t, n, vel, gate) for n in notes)
        t += period
    return evs


PHRASES: dict[str, tuple[float, list[NoteEv]]] = {
    # target A: At Your Best pad - slow Am voicing, 45+57+60+62+64+69
    "A": (13.0, hold([45, 57, 60, 62, 64, 69], 0.2, 9.0, 88)),
    # target B: Mitsubushi pumping chords - Gm11 eighth pulses then hold
    "B": (13.0, pulses([43, 58, 62, 67, 72], 0.2, 6.2, 0.25, 0.17, 105)
          + hold([43, 58, 62, 67, 72], 6.45, 3.0, 105)),
    # target C: Impietas drone - stacked fourths B1 F#3 B3 E4
    "C": (17.0, hold([35, 54, 59, 64], 0.2, 12.0, 92)),
    # target D: Hublots comp - Cm7 quarter stabs
    "D": (11.0, pulses([48, 55, 60, 63, 67, 70], 0.2, 6.2, 0.75, 0.55, 96)),
}

# reference stems + analysis window (sustained, representative part)
REF_SPECS = {
    "A": ("A-atyourbest-outro-stem.wav", 2.0, 22.0),
    "B": ("B-mitsubushi-chords-stem.wav", 12.0, 38.0),
    "C": ("C-impietas-drone-stem.wav", 2.0, 30.0),
    "D": ("D-hublots-lead-stem.wav", 2.0, 55.0),
}


# ------------------------------------------------------------- candidates ---
@dataclass(frozen=True)
class Cand:
    key: str            # e.g. "A1-bellpad"
    target: str         # "A".."D"
    base: str           # factory patch path relative to patches_factory
    tweaks: tuple[tuple[str, str], ...] = ()   # (param name substr, display target)


CANDS = (
    Cand("A1-bellpad", "A", "Pads/Bell Pad.fxp",
         (("Amp EG Attack", "0.55 s"), ("Amp EG Release", "2.5 s"))),
    Cand("A2-fmpad", "A", "Pads/FM Pad.fxp",
         (("Amp EG Attack", "0.55 s"),)),
    Cand("A3-mks70", "A", "Pads/MKS-70 Warm Pad.fxp",
         (("Amp EG Attack", "0.55 s"),)),
    Cand("B1-jupiter8", "B", "Polysynths/Jupiter-8.fxp",
         (("Amp EG Attack", "5.0 ms"), ("Amp EG Release", "0.30 s"))),
    Cand("B2-juno60", "B", "Polysynths/Juno-60 Strings.fxp",
         (("Amp EG Attack", "10.0 ms"), ("Amp EG Release", "0.30 s"))),
    Cand("B3-anthemish", "B", "Polysynths/Anthemish 1.fxp",
         (("Amp EG Attack", "5.0 ms"), ("Amp EG Release", "0.30 s"))),
    Cand("C1-ghostpad", "C", "Pads/Ghost Pad.fxp",
         (("Amp EG Attack", "0.70 s"),)),
    Cand("C2-distant", "C", "Pads/Distant.fxp",
         (("Amp EG Attack", "0.70 s"),)),
    Cand("C3-choirpad", "C", "Pads/Choir Pad Thing.fxp",
         (("Amp EG Attack", "0.70 s"),)),
    Cand("D1-suitcase", "D", "Keys/Soft Suitcase.fxp"),
    Cand("D2-dxep", "D", "Keys/DX EP.fxp"),
    Cand("D3-houseorgan", "D", "Keys/House Organ.fxp"),
    # --- round 2: brightness fixes guided by profile-compare.png ---
    Cand("A2b-fmpad-dark", "A", "Pads/FM Pad.fxp",
         (("Amp EG Attack", "0.55 s"), ("Filter 1 Cutoff", "1800.0 Hz"))),
    Cand("A2c-fmpad-darker", "A", "Pads/FM Pad.fxp",
         (("Amp EG Attack", "0.55 s"), ("Filter 1 Cutoff", "1000.0 Hz"))),
    Cand("D2b-dxep-dark", "D", "Keys/DX EP.fxp",
         (("Filter 1 Cutoff", "3000.0 Hz"),)),
)


# ------------------------------------------------------------ param utils ---
def walk_params(obj, out: dict):
    """Collect SurgeNamedParam objects from the nested patch dict."""
    if isinstance(obj, dict):
        for v in obj.values():
            walk_params(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            walk_params(v, out)
    else:
        r = repr(obj)
        if "SurgeNamedParam" in r:
            m = re.search(r"'(.+)'", r)
            if m:
                out[m.group(1)] = obj


def parse_display(txt: str) -> float | None:
    m = re.search(r"(-?\d+\.?\d*)", txt.replace(",", ""))
    if not m:
        return None
    val = float(m.group(1))
    if "ms" in txt:
        val /= 1000.0
    if "kHz" in txt:
        val *= 1000.0
    return val


def set_by_display(s, param, target_txt: str) -> bool:
    """Binary-search raw param value until the display matches target_txt."""
    target = parse_display(target_txt)
    if target is None:
        return False
    if " ms" in target_txt:
        pass  # parse_display already normalised to seconds
    lo, hi = s.getParamMin(param), s.getParamMax(param)
    for _ in range(60):
        mid = (lo + hi) / 2
        s.setParamVal(param, mid)
        cur = parse_display(s.getParamDisplay(param))
        if cur is None:
            return False
        if abs(cur - target) <= max(0.005 * abs(target), 1e-4):
            return True
        if cur < target:
            lo = mid
        else:
            hi = mid
    return False


# -------------------------------------------------------------- rendering ---
def render(s, phrase: list[NoteEv], dur: float) -> np.ndarray:
    bs = s.getBlockSize()
    nblocks = int(dur * SR / bs)
    buf = s.createMultiBlock(nblocks)
    events = []  # (block, kind, note, vel)
    for ev in phrase:
        events.append((int(ev.t * SR / bs), 1, ev.note, ev.vel))
        events.append((int((ev.t + ev.dur) * SR / bs), 0, ev.note, 0))
    events.sort(key=lambda e: e[0])
    pos = 0
    for blk, kind, note, vel in events:
        if blk > pos:
            s.processMultiBlock(buf, pos, blk - pos)
            pos = blk
        if kind:
            s.playNote(0, note, vel, 0)
        else:
            s.releaseNote(0, note, 0)
    if nblocks > pos:
        s.processMultiBlock(buf, pos, nblocks - pos)
    return buf.T  # (n, 2)


def band_profile(y: np.ndarray, sr: int) -> np.ndarray:
    """Mean log-power in 60 log-spaced bands 60Hz-10kHz."""
    mono = y.mean(axis=1) if y.ndim == 2 else y
    n_fft = 16384
    hop = 4096
    nfr = max(1, (len(mono) - n_fft) // hop)
    win = np.hanning(n_fft)
    acc = np.zeros(n_fft // 2 + 1)
    for i in range(nfr):
        fr = mono[i * hop: i * hop + n_fft] * win
        acc += np.abs(np.fft.rfft(fr)) ** 2
    acc /= nfr
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    edges = np.geomspace(60, 10000, 61)
    prof = np.array([
        acc[(freqs >= edges[i]) & (freqs < edges[i + 1])].mean() + 1e-12
        for i in range(60)
    ])
    # fill any empty band by interpolating over band index
    bad = ~np.isfinite(prof)
    if bad.any():
        idx = np.arange(60)
        prof[bad] = np.interp(idx[bad], idx[~bad], prof[~bad])
    db = 10 * np.log10(prof)
    return db - db.max()


def spectral_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(((a - b) ** 2).mean()))


def set_enum_by_display(s, param, name: str) -> bool:
    """Scan an enum-ish param until its display contains name."""
    lo, hi = int(s.getParamMin(param)), int(s.getParamMax(param))
    for v in range(lo, hi + 1):
        s.setParamVal(param, v)
        if name.lower() in s.getParamDisplay(param).lower():
            return True
    return False


def set_fx_type_by_name(s, fx, name: str) -> bool:
    t = fx["type"]
    for v in range(int(s.getParamMax(t)) + 1):
        s.setParamVal(t, v)
        if name.lower() in s.getParamDisplay(t).lower():
            return True
    s.setParamVal(t, 0)
    return False


def build_c4_darkdrone(s) -> None:
    """Dark stacked-fourths drone: Ghost Pad FX chain, oscs reshaped to dark sines."""
    s.loadPatch(str(FACTORY / "Pads/Ghost Pad.fxp"))
    patch = s.getPatch()
    sc = patch["scene"][0]
    s.setParamVal(sc["osc"][0]["type"], 1)            # osc1 -> Sine
    patch = s.getPatch()                               # re-fetch after type change
    sc = patch["scene"][0]
    params: dict = {}
    walk_params(patch, params)

    def setp(substr: str, disp: str) -> None:
        hits = [k for k in params if substr in k and k.startswith("A ")]
        hits = hits or [k for k in params if substr in k]
        if hits:
            set_by_display(s, params[hits[0]], disp)

    setp("Osc 1 Feedback", "40.00 %")
    setp("Filter 1 Cutoff", "900.0 Hz")
    setp("Amp EG Attack", "0.70 s")
    setp("Amp EG Release", "3.5 s")
    setp("Osc Drift", "35.00 %")
    setp("Noise Volume", "-28.00 dB")
    setp("LFO 1 Rate", "1.00 Hz")
    if "A Noise Mute" in params:
        s.setParamVal(params["A Noise Mute"], 0)
    # slow pitch wobble ~ +-40 cents via LFO1 -> scene pitch
    lfo1 = s.getModSource(surgepy.constants.ms_lfo1)
    if s.isValidModulation(sc["pitch"], lfo1):
        s.setModDepth01(sc["pitch"], lfo1, 0.028)


CUSTOM_BUILDERS = {"C4-darkdrone": ("C", build_c4_darkdrone)}


def main() -> None:
    OUT_WAV.mkdir(parents=True, exist_ok=True)
    OUT_FXP.mkdir(exist_ok=True)

    ref_profiles = {}
    for tgt, (fname, t0, t1) in REF_SPECS.items():
        y, sr = sf.read(REFS / fname, dtype="float32")
        ref_profiles[tgt] = band_profile(y[int(t0 * sr): int(t1 * sr)], sr)

    results = []
    for cand in CANDS:
        s = surgepy.createSurge(SR)
        s.loadPatch(str(FACTORY / cand.base))
        params: dict = {}
        walk_params(s.getPatch(), params)
        applied = []
        for substr, disp in cand.tweaks:
            hits = [k for k in params if substr in k and k.startswith("A ")]
            hits = hits or [k for k in params if substr in k]
            if hits and set_by_display(s, params[hits[0]], disp):
                applied.append(f"{hits[0]}={disp}")
        dur, phrase = PHRASES[cand.target]
        y = render(s, phrase, dur)
        peak = np.abs(y).max() + 1e-9
        y = y * (10 ** (-6 / 20) / peak)
        wav = OUT_WAV / f"{cand.key}.wav"
        sf.write(wav, y, SR)
        rms_db = 20 * math.log10(float(np.sqrt((y ** 2).mean())) + 1e-9)
        # score on the sustained body only (skip attack second and tail)
        body = y[int(1.5 * SR): int((dur - 3.0) * SR)]
        dist = spectral_distance(band_profile(body, SR), ref_profiles[cand.target])
        s.savePatch(str(OUT_FXP / f"{cand.key}.fxp"))
        results.append({"cand": cand.key, "target": cand.target, "base": cand.base,
                        "dist": round(dist, 2), "tweaks": applied})
        print(f"{cand.key:16s} dist={dist:6.2f} rms={rms_db:6.1f}dB  tweaks={applied}", flush=True)

    for key, (tgt, builder) in CUSTOM_BUILDERS.items():
        s = surgepy.createSurge(SR)
        builder(s)
        dur, phrase = PHRASES[tgt]
        y = render(s, phrase, dur)
        peak = np.abs(y).max() + 1e-9
        y = y * (10 ** (-6 / 20) / peak)
        sf.write(OUT_WAV / f"{key}.wav", y, SR)
        rms_db = 20 * math.log10(float(np.sqrt((y ** 2).mean())) + 1e-9)
        body = y[int(1.5 * SR): int((dur - 3.0) * SR)]
        dist = spectral_distance(band_profile(body, SR), ref_profiles[tgt])
        s.savePatch(str(OUT_FXP / f"{key}.fxp"))
        results.append({"cand": key, "target": tgt, "base": "custom-init",
                        "dist": round(dist, 2), "tweaks": ["builder"]})
        print(f"{key:16s} dist={dist:6.2f} rms={rms_db:6.1f}dB  tweaks=[builder]", flush=True)

    (BASE / "render-scores.json").write_text(json.dumps(results, indent=1))
    best = {}
    for r in results:
        if r["target"] not in best or r["dist"] < best[r["target"]]["dist"]:
            best[r["target"]] = r
    print("\nbest per target:")
    for tgt in sorted(best):
        print(f"  {tgt}: {best[tgt]['cand']} (dist {best[tgt]['dist']})")


if __name__ == "__main__":
    main()
