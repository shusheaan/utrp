"""Target audio + base Surge patch -> parameter-refined patch (closed loop).

The neurosymbolic v0, symbolic half: the synth's parameter space is the
program, and we search it against a perceptual distance (60-band log spectrum
+ centroid + attack, shared with pipeline browse). Coordinate descent over a
whitelist of high-impact parameters, rendering the probe phrase each step via
surgepy. Pairs with pipeline `browse` (global preset search) the way
Genopatch pairs evolution with its own engine — except this targets Surge and
every result stays a human-tweakable .fxp.

Usage (venv-render python):
  python refine.py <target.wav> <base> <out.fxp>
      [--notes 48,55,60,64] [--sweeps 3] [--params "Cutoff,Resonance,..."]
  base: factory:<rel> | lib:<collection>/<name>.fxp | plain path
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import surgepy

sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))
from albumspec import CandidateSpec, PhraseNote  # noqa: E402
from spectral import attack_ms, band_profile, centroid_track  # noqa: E402
from synth import SR, probe_distance, render_phrase, walk_params  # noqa: E402

DEFAULT_PARAMS = ("Filter 1 Cutoff", "Filter 1 Resonance", "Amp EG Attack",
                  "Amp EG Decay", "Amp EG Sustain", "Amp EG Release",
                  "Osc Drift", "Osc 1 Width")
PROBE_DUR = 5.0


def resolve(base: str) -> Path:
    if ":" in base and not Path(base).exists():
        return CandidateSpec("x", base, ()).base_path()
    return Path(base)


def phrase_of(notes: list[int]) -> tuple[PhraseNote, ...]:
    return tuple(PhraseNote(0.2, n, 92, 3.2) for n in notes)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("--notes", default="48,55,60,64")
    ap.add_argument("--sweeps", type=int, default=3)
    ap.add_argument("--params", default=",".join(DEFAULT_PARAMS))
    args = ap.parse_args()

    ref, rsr = sf.read(args.target, dtype="float32", always_2d=True)
    mono = ref.mean(axis=1)
    ref_prof = band_profile(ref, rsr)
    ref_cent = float(np.median(centroid_track(mono, rsr)))
    ref_atk = attack_ms(mono[:int(4 * rsr)], rsr) or 200.0

    s = surgepy.createSurge(SR)
    s.loadPatch(str(resolve(args.base)))
    all_params: dict = {}
    walk_params(s.getPatch(), all_params)
    wanted = [w.strip() for w in args.params.split(",") if w.strip()]
    targets = []
    for w in wanted:
        hits = [k for k in all_params if w in k and k.startswith("A ")]
        hits = hits or [k for k in all_params if w in k]
        if hits:
            targets.append((hits[0], all_params[hits[0]]))
    if not targets:
        raise SystemExit("no whitelisted params found in this patch")

    phrase = phrase_of([int(n) for n in args.notes.split(",")])

    def dist() -> float:
        y = render_phrase(s, phrase, PROBE_DUR)
        peak = float(np.abs(y).max())
        if peak < 1e-6:
            return 999.0
        return probe_distance(y * (10 ** (-6 / 20) / peak), PROBE_DUR,
                              ref_prof, ref_cent, ref_atk)

    d0 = best = dist()
    print(f"start dist {d0:.2f}  ({len(targets)} params: "
          + ", ".join(k for k, _ in targets) + ")")
    step = 0.15
    for sweep in range(args.sweeps):
        for name, p in targets:
            lo, hi = s.getParamMin(p), s.getParamMax(p)
            cur = s.getParamVal(p)
            for delta in (step, -step):
                cand = min(hi, max(lo, cur + delta * (hi - lo)))
                if cand == cur:
                    continue
                s.setParamVal(p, cand)
                d = dist()
                if d < best - 1e-3:
                    best, cur = d, cand
                    print(f"  {name}: -> {s.getParamDisplay(p)}  dist {d:.2f}")
                else:
                    s.setParamVal(p, cur)
        step *= 0.5
        print(f"sweep {sweep + 1}: dist {best:.2f}")

    s.savePatch(str(Path(args.out)))
    y = render_phrase(s, phrase, PROBE_DUR)
    sf.write(str(Path(args.out).with_suffix(".wav")),
             y * (10 ** (-6 / 20) / (np.abs(y).max() + 1e-9)), SR)
    print(f"dist {d0:.2f} -> {best:.2f}  "
          f"({(1 - best / d0) * 100:.0f}% closer)  saved {args.out} (+.wav)")


if __name__ == "__main__":
    main()
