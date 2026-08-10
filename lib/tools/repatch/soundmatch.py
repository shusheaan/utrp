"""Local Sonaura-Match-style instant preset search over the Surge library.

Difference from pipeline `browse`: browse re-renders the whole library per
target (slow, phrase-matched); this pre-renders every patch ONCE with a
standard probe and stores a feature index, so any later query answers in
milliseconds. Like Sonaura Match it offers weighting modes (general / pad /
pluck / tone); unlike it, every hit is a Surge patch you can open, and the
result feeds straight into refine.py for parameter fine-tuning.

Usage (venv-render python):
  python soundmatch.py build [path-filter ...]     # render + index (one-off)
  python soundmatch.py find <target.wav> [--mode pad] [--n 15] [--t0 S --t1 S]
Index lives in ~/storage/daw/repatch-index/ (rebuild-safe, incremental).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))
from albumspec import FACTORY, LIB_ROOT, PhraseNote  # noqa: E402
from spectral import attack_ms, band_profile, centroid_track, mod_features  # noqa: E402

INDEX_DIR = Path.home() / "storage/daw/repatch-index"
PROBE = tuple(PhraseNote(0.1, n, 92, 2.8) for n in (48, 55, 60, 64))
PROBE_DUR = 4.0
MODES = {  # weights: (bands, centroid, attack, mod)
    "general": (1.0, 3.0, 1.2, 0.5),
    "pad":     (1.0, 2.0, 0.4, 2.0),
    "pluck":   (0.8, 2.0, 3.0, 0.2),
    "tone":    (1.5, 4.0, 0.2, 0.2),
}


def wav_features(y: np.ndarray, sr: int) -> dict:
    mono = y.mean(axis=1) if y.ndim == 2 else y
    mod = mod_features(mono, sr)
    return {
        "bands": band_profile(y, sr).tolist(),
        "cent": float(np.log2(np.median(centroid_track(mono, sr)) + 1)),
        "atk": float(np.log((attack_ms(mono[:int(4 * sr)], sr) or 200) + 20)),
        "mod": float(mod["trem_depth"] + mod["bright_depth"]),
    }


def distance(a: dict, b: dict, mode: str) -> float:
    wb, wc, wa, wm = MODES[mode]
    d_bands = float(np.sqrt(((np.array(a["bands"]) - np.array(b["bands"])) ** 2
                             ).mean()))
    return (wb * d_bands + wc * abs(a["cent"] - b["cent"])
            + wa * abs(a["atk"] - b["atk"]) + wm * abs(a["mod"] - b["mod"]))


# ------------------------------------------------------------------- build ---
def patch_list(filters: list[str]) -> list[tuple[str, Path]]:
    out = []
    for sub in ("patches_factory", "patches_3rdparty"):
        for p in sorted((FACTORY / sub).rglob("*.fxp")):
            out.append((f"factory:{p.relative_to(FACTORY / sub)}", p))
    for p in sorted((LIB_ROOT / "surge").rglob("*.fxp")):
        out.append((f"lib:{p.relative_to(LIB_ROOT / 'surge')}", p))
    if filters:
        out = [(r, p) for r, p in out
               if any(f.lower() in r.lower() for f in filters)]
    return out


def cmd_build(filters: list[str]) -> None:
    import surgepy
    from synth import SR, render_phrase
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    idx_file = INDEX_DIR / "index.json"
    idx: dict = json.loads(idx_file.read_text()) if idx_file.exists() else {}
    todo = [(r, p) for r, p in patch_list(filters) if r not in idx]
    print(f"{len(todo)} patches to index ({len(idx)} already done)")
    for i, (rel, p) in enumerate(todo):
        try:
            s = surgepy.createSurge(SR)
            s.loadPatch(str(p))
            y = render_phrase(s, PROBE, PROBE_DUR)
            peak = float(np.abs(y).max())
            if peak < 1e-6:
                idx[rel] = None                    # silent patch: skip forever
            else:
                idx[rel] = wav_features(y * (10 ** (-6 / 20) / peak), SR)
        except Exception as e:                      # corrupt patch zoo
            print(f"  skip {rel}: {e}", flush=True)
            idx[rel] = None
        if (i + 1) % 25 == 0:
            idx_file.write_text(json.dumps(idx))
            print(f"  {i + 1}/{len(todo)}", flush=True)
    idx_file.write_text(json.dumps(idx))
    ok = sum(1 for v in idx.values() if v)
    print(f"index: {ok} usable / {len(idx)} total -> {idx_file}")


# -------------------------------------------------------------------- find ---
def cmd_find(target: str, mode: str, n: int, t0: float, t1: float | None) -> None:
    idx_file = INDEX_DIR / "index.json"
    if not idx_file.exists():
        raise SystemExit("no index yet — run: soundmatch.py build")
    idx = {k: v for k, v in json.loads(idx_file.read_text()).items() if v}
    y, sr = sf.read(target, dtype="float32", always_2d=True)
    y = y[int(t0 * sr): int((t1 or len(y) / sr) * sr)]
    q = wav_features(y, sr)
    ranked = sorted((distance(q, v, mode), k) for k, v in idx.items())
    print(f"target {Path(target).name}  mode={mode}  "
          f"(index: {len(idx)} patches)\n")
    for d, k in ranked[:n]:
        print(f"  {d:6.2f}  {k}")
    print("\nnext: refine the winner —")
    d, k = ranked[0]
    print(f"  python refine.py '{target}' '{k}' out.fxp")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("filters", nargs="*")
    f = sub.add_parser("find")
    f.add_argument("target")
    f.add_argument("--mode", default="general", choices=sorted(MODES))
    f.add_argument("--n", type=int, default=15)
    f.add_argument("--t0", type=float, default=0.0)
    f.add_argument("--t1", type=float, default=None)
    args = ap.parse_args()
    if args.cmd == "build":
        cmd_build(args.filters)
    else:
        cmd_find(args.target, args.mode, args.n, args.t0, args.t1)


if __name__ == "__main__":
    main()
