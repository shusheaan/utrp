"""REAPER-facing half of the soundmatch bridge (surgepy venv).

Called by tools/reaper/utrp_soundmatch.lua via ExecProcess: takes the source
file + span of the selected item, finds top-K patches in the prebuilt index,
renders a short audition preview for each via surgepy, and prints a TSV
protocol that Lua can parse without a JSON library:

  CAND\t<rank>\t<dist>\t<patch-ref>\t<preview-wav-abs-path>

Previews land in ~/storage/daw/repatch-previews/<slug>/ (not in git).

Usage: python reabridge.py <audio> [--t0 S] [--t1 S] [--mode pad] [--k 5]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))
from albumspec import CandidateSpec  # noqa: E402
from soundmatch import INDEX_DIR, MODES, PROBE, PROBE_DUR, distance, wav_features  # noqa: E402

PREVIEW_DIR = Path.home() / "storage/daw/repatch-previews"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--t0", type=float, default=0.0)
    ap.add_argument("--t1", type=float, default=None)
    ap.add_argument("--mode", default="pad", choices=sorted(MODES))
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    idx_file = INDEX_DIR / "index.json"
    if not idx_file.exists():
        print("ERR\tno index — run soundmatch.py build first")
        return
    idx = {k: v for k, v in json.loads(idx_file.read_text()).items() if v}

    y, sr = sf.read(args.audio, dtype="float32", always_2d=True)
    y = y[int(args.t0 * sr): int((args.t1 or len(y) / sr) * sr)]
    if not len(y):
        print("ERR\tempty selection span")
        return
    q = wav_features(y, sr)
    ranked = sorted((distance(q, v, args.mode), k) for k, v in idx.items())

    import surgepy
    from synth import SR, render_phrase
    slug = re.sub(r"[^A-Za-z0-9]+", "-", Path(args.audio).stem).strip("-").lower()
    out = PREVIEW_DIR / f"{slug}-{args.mode}"
    out.mkdir(parents=True, exist_ok=True)
    for rank, (d, rel) in enumerate(ranked[: args.k], 1):
        try:
            path = CandidateSpec("x", rel, ()).base_path() if ":" in rel \
                else Path(rel)
            s = surgepy.createSurge(SR)
            s.loadPatch(str(path))
            yy = render_phrase(s, PROBE, PROBE_DUR)
            yy = yy * (10 ** (-8 / 20) / (np.abs(yy).max() + 1e-9))
            wav = out / f"{rank:02d}.wav"
            sf.write(wav, yy, SR)
            print(f"CAND\t{rank}\t{d:.2f}\t{rel}\t{wav}")
        except Exception as e:                      # corrupt patch: drop rank
            print(f"ERR\t{rel}: {e}")


if __name__ == "__main__":
    main()
