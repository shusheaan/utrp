"""Sega Bodega 'I Created The Universe...' signature-timbre candidates.

Reuses the endless pipeline (render.py) with album-specific targets/candidates.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import surgepy

sys.path.insert(0, str(Path(__file__).parent))
import render as R  # noqa: E402
from render import NoteEv, hold, walk_params, set_by_display  # noqa: E402

BASE = Path(__file__).parent
FACTORY = Path("/usr/share/surge-xt")
REFS = BASE / "sega-targets"
OUT_WAV = Path.home() / "storage/daw/sega-universe/renders"
OUT_FXP = BASE / "sega-patches"

PHRASES = {
    # S1 warm wall: B 6/9 stack, long hold
    "S1": (15.0, hold([47, 54, 59, 63, 66, 71, 73], 0.2, 11.0, 84)),
    # S2 swell: three 4s-period swells of a Bmaj7 stack (patch attack does the work)
    "S2": (17.0, hold([47, 54, 58, 63, 66], 0.3, 3.6, 96)
          + hold([47, 54, 58, 63, 66], 4.5, 3.6, 96)
          + hold([47, 54, 58, 63, 66], 8.7, 3.6, 96)),
    # S3 soft lead noodle in B major upper register
    "S3": (16.0, [NoteEv(0.3, 64, 78, 1.6), NoteEv(2.0, 66, 80, 1.6),
                  NoteEv(3.8, 68, 82, 1.8), NoteEv(5.8, 71, 86, 2.2),
                  NoteEv(8.2, 73, 84, 1.8), NoteEv(10.2, 75, 82, 2.6)]),
    # S4 shimmer wall: Bb major stack, long hold
    "S4": (18.0, hold([46, 53, 58, 62, 65, 70, 72], 0.2, 13.0, 90)),
}

REF_SPECS = {
    "S1": ("S1-pipe-wall-stem.wav", 2.0, 38.0),
    "S2": ("S2-cradle-swell-stem.wav", 2.0, 42.0),
    "S3": ("S3-cradle-lead-stem.wav", 2.0, 40.0),
    "S4": ("S4-universe-shimmer-stem.wav", 2.0, 70.0),
}

CANDS = (
    ("S1a-mks70", "S1", "patches_factory/Pads/MKS-70 Warm Pad.fxp",
     (("Amp EG Attack", "0.45 s"),)),
    ("S1b-ooh", "S1", "patches_factory/Pads/Ooh.fxp",
     (("Amp EG Attack", "0.45 s"),)),
    ("S1c-stringmachine", "S1", "patches_3rdparty/Jacky Ligon/Pads/String Machine 11.fxp",
     (("Amp EG Attack", "0.45 s"),)),
    ("S2a-ghost-swell", "S2", "patches_factory/Pads/Ghost Pad.fxp",
     (("Amp EG Attack", "1.6 s"), ("Amp EG Release", "1.2 s"))),
    ("S2b-newwaves", "S2", "patches_3rdparty/Jacky Ligon/Atmospheres/New Waves.fxp",
     (("Amp EG Attack", "1.6 s"), ("Amp EG Release", "1.2 s"))),
    ("S2c-distant-swell", "S2", "patches_factory/Pads/Distant.fxp",
     (("Amp EG Attack", "1.6 s"), ("Amp EG Release", "1.2 s"))),
    ("S3a-winds", "S3", None, ()),          # filled below after listing Winds
    ("S4a-darkpulse", "S4", "patches_3rdparty/Altenberg/Pads/Dark Pulse.fxp",
     (("Amp EG Attack", "0.35 s"),)),
    ("S4b-manaquest", "S4", "patches_3rdparty/Altenberg/Pads/Mana Quest.fxp",
     (("Amp EG Attack", "0.35 s"),)),
    ("S4c-moire", "S4", "patches_3rdparty/Jacky Ligon/Soundscapes/Moire 1.fxp",
     (("Amp EG Attack", "0.35 s"),)),
)


def main() -> None:
    OUT_WAV.mkdir(parents=True, exist_ok=True)
    OUT_FXP.mkdir(exist_ok=True)

    ref_profiles = {}
    for tgt, (fname, t0, t1) in REF_SPECS.items():
        y, sr = sf.read(REFS / fname, dtype="float32")
        ref_profiles[tgt] = R.band_profile(y[int(t0 * sr): int(t1 * sr)], sr)

    # S3 soft lead: pick three Winds/Leads patches that exist
    s3_bases = []
    for cand in ("patches_factory/Winds/Breathy Chiff.fxp",
                 "patches_factory/Winds/Pan Flute.fxp",
                 "patches_factory/Winds/Recorder.fxp",
                 "patches_factory/Winds/Shakuhachi.fxp",
                 "patches_factory/Leads/Soft Lead.fxp"):
        if (FACTORY / cand).exists():
            s3_bases.append(cand)
        if len(s3_bases) == 3:
            break
    if not s3_bases:  # fall back to whatever Winds ships
        s3_bases = [f"patches_factory/Winds/{p.name}" for p in
                    sorted((FACTORY / "patches_factory/Winds").glob("*.fxp"))[:3]]
    cands = [c for c in CANDS if c[0] != "S3a-winds"]
    for i, b in enumerate(s3_bases):
        slug = Path(b).stem.lower().replace(" ", "")[:12]
        cands.append((f"S3{'abc'[i]}-{slug}", "S3", b, ()))

    results = []
    for key, tgt, base, tweaks in cands:
        s = surgepy.createSurge(R.SR)
        s.loadPatch(str(FACTORY / base))
        params: dict = {}
        walk_params(s.getPatch(), params)
        applied = []
        for substr, disp in tweaks:
            hits = [k for k in params if substr in k and k.startswith("A ")]
            hits = hits or [k for k in params if substr in k]
            if hits and set_by_display(s, params[hits[0]], disp):
                applied.append(f"{substr}={disp}")
        dur, phrase = PHRASES[tgt]
        y = R.render(s, phrase, dur)
        peak = np.abs(y).max() + 1e-9
        y = y * (10 ** (-6 / 20) / peak)
        sf.write(OUT_WAV / f"{key}.wav", y, R.SR)
        rms_db = 20 * math.log10(float(np.sqrt((y ** 2).mean())) + 1e-9)
        body = y[int(1.5 * R.SR): int((dur - 3.0) * R.SR)]
        dist = R.spectral_distance(R.band_profile(body, R.SR), ref_profiles[tgt])
        s.savePatch(str(OUT_FXP / f"{key}.fxp"))
        results.append({"cand": key, "target": tgt, "base": base,
                        "dist": round(dist, 2), "tweaks": applied})
        print(f"{key:22s} dist={dist:6.2f} rms={rms_db:6.1f}dB {applied}", flush=True)

    (BASE / "sega-scores.json").write_text(json.dumps(results, indent=1))
    best = {}
    for r in results:
        if r["target"] not in best or r["dist"] < best[r["target"]]["dist"]:
            best[r["target"]] = r
    print("\nbest per target:")
    for tgt in sorted(best):
        print(f"  {tgt}: {best[tgt]['cand']} (dist {best[tgt]['dist']})")


if __name__ == "__main__":
    main()
