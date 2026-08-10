"""Synthesis side of the pipeline (surgepy venv): render / score / project / browse.

Usage:
  python synth.py <spec.toml> render    # candidates -> renders/ + scores + fxp into lib
  python synth.py <spec.toml> project   # assemble <name>.rpp (incl. drum groups if any)
  python synth.py <spec.toml> all
  python synth.py <spec.toml> browse <target> [path-filter ...]
      # rank the whole factory/3rdparty patch library against the target's ref
      # stem with a short probe render; prints paste-ready candidate lines.
      # Incremental: cached per patch in <proj>/browse/. Full scan ~3000
      # patches; narrow with filters ("Pads", "Jacky Ligon", ...) first.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import surgepy

sys.path.insert(0, str(Path(__file__).parent))
import rpp  # noqa: E402
from albumspec import FACTORY, LIB_ROOT, AlbumSpec, PhraseNote, TargetSpec, load  # noqa: E402
from spectral import attack_ms, band_profile, centroid_track, spectral_distance  # noqa: E402

SR = 48000


# ------------------------------------------------------------ surge params ---
def walk_params(obj, out: dict) -> None:
    if isinstance(obj, dict):
        for v in obj.values():
            walk_params(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            walk_params(v, out)
    else:
        r = repr(obj)
        if "SurgeNamedParam" in r:
            import re
            m = re.search(r"'(.+)'", r)
            if m:
                out[m.group(1)] = obj


def parse_display(txt: str) -> float | None:
    import re
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
    target = parse_display(target_txt)
    if target is None:
        return False
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


def render_phrase(s, phrase, dur: float) -> np.ndarray:
    bs = s.getBlockSize()
    nblocks = int(dur * SR / bs)
    buf = s.createMultiBlock(nblocks)
    events = []
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
    return buf.T


# ------------------------------------------------------------------ render ---
def cmd_render(spec: AlbumSpec) -> None:
    renders = spec.project_dir / "renders"
    renders.mkdir(parents=True, exist_ok=True)
    # savePatch goes to a storage staging dir: writing into lib/ directly can
    # wake Surge's PatchDB (sqlite) which crashes when another Surge instance
    # (e.g. inside a running REAPER) holds the database. cmd_install copies.
    staging = spec.project_dir / "patches"
    staging.mkdir(exist_ok=True)

    results = []
    for tg in spec.targets:
        ref, sr = sf.read(spec.project_dir / "refs" / f"{tg.key}-stem.wav",
                          dtype="float32")
        w0, w1 = tg.score_window
        ref_prof = band_profile(ref[int(w0 * sr): int(w1 * sr)], sr)
        for cand in tg.candidates:
            s = surgepy.createSurge(SR)
            s.loadPatch(str(cand.base_path()))
            params: dict = {}
            walk_params(s.getPatch(), params)
            applied = []
            for substr, disp in cand.tweaks:
                hits = [k for k in params if substr in k and k.startswith("A ")]
                hits = hits or [k for k in params if substr in k]
                if hits and set_by_display(s, params[hits[0]], disp):
                    applied.append(substr)
            y = render_phrase(s, tg.phrase, tg.phrase_dur)
            y = y * (10 ** (-6 / 20) / (np.abs(y).max() + 1e-9))
            sf.write(renders / f"{cand.key}.wav", y, SR)
            body = y[int(1.5 * SR): int((tg.phrase_dur - 2.5) * SR)]
            dist = spectral_distance(band_profile(body, SR), ref_prof)
            s.savePatch(str(staging / f"{cand.key}.fxp"))
            results.append({"cand": cand.key, "target": tg.short,
                            "dist": round(dist, 2), "tweaks": applied})
            print(f"{cand.key:22s} dist={dist:6.2f}", flush=True)
    (spec.project_dir / "scores.json").write_text(json.dumps(results, indent=1))
    cmd_install(spec)


def cmd_install(spec: AlbumSpec) -> None:
    """Plain-copy staged fxp into lib/surge/<collection> (no Surge involved)."""
    import shutil
    staging = spec.project_dir / "patches"
    patch_dir = LIB_ROOT / "surge" / spec.collection
    try:
        patch_dir.mkdir(parents=True, exist_ok=True)
        for f in sorted(staging.glob("*.fxp")):
            shutil.copy(f, patch_dir / f.name)
        print(f"installed {len(list(staging.glob('*.fxp')))} patches -> {patch_dir}")
    except OSError as e:
        print(f"install blocked ({e}); rerun: synth.py <spec> install")


# ------------------------------------------------------------------ browse ---
PROBE_DUR = 6.0


def probe_phrase(tg: TargetSpec) -> tuple[tuple[PhraseNote, ...], float]:
    """First ~4 s of the target phrase, tails clipped, for cheap scan renders."""
    notes = tuple(PhraseNote(ev.t, ev.note, ev.vel, min(ev.dur, 4.0 - ev.t))
                  for ev in tg.phrase if ev.t < 4.0)
    return notes, min(tg.phrase_dur, PROBE_DUR)


def ref_features(spec: AlbumSpec, tg: TargetSpec) -> tuple[np.ndarray, float, float]:
    ref, sr = sf.read(spec.project_dir / "refs" / f"{tg.key}-stem.wav",
                      dtype="float32")
    w0, w1 = tg.score_window
    cut = ref[int(w0 * sr): int(w1 * sr)]
    mono = cut.mean(axis=1)
    cent = float(np.median(centroid_track(mono, sr)))
    atk = attack_ms(mono[:int(4.0 * sr)], sr) or 200.0
    return band_profile(cut, sr), cent, atk


def probe_distance(y: np.ndarray, dur: float, ref_prof: np.ndarray,
                   ref_cent: float, ref_atk: float) -> float:
    body = y[int(0.5 * SR): int((dur - 1.0) * SR)]
    mono = body.mean(axis=1)
    if np.abs(mono).max() < 1e-5:
        return 999.0
    d = spectral_distance(band_profile(body, SR), ref_prof)
    cent = float(np.median(centroid_track(mono, SR)))
    atk = attack_ms(y.mean(axis=1), SR) or 200.0
    d += 3.0 * abs(np.log2(cent / ref_cent))
    d += 1.2 * abs(np.log2((atk + 20.0) / (ref_atk + 20.0)))
    return float(d)


def cmd_browse(spec: AlbumSpec, args: list[str]) -> None:
    if not args:
        raise SystemExit("browse needs a target key (e.g. M1 or M1-teyes-drone)")
    want, filters = args[0], args[1:]
    tg = next(t for t in spec.targets if t.key == want or t.short == want)
    phrase, dur = probe_phrase(tg)
    ref_prof, ref_cent, ref_atk = ref_features(spec, tg)

    paths = []
    for sub in ("patches_factory", "patches_3rdparty"):
        for p in sorted((FACTORY / sub).rglob("*.fxp")):
            rel = f"{sub}:{p.relative_to(FACTORY / sub)}"
            if not filters or any(f.lower() in rel.lower() for f in filters):
                paths.append((rel, p))

    cache_file = spec.project_dir / "browse" / f"{tg.short}-scores.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    scores: dict[str, float] = (json.loads(cache_file.read_text())
                                if cache_file.exists() else {})
    todo = [(rel, p) for rel, p in paths if rel not in scores]
    print(f"{tg.key}: {len(paths)} patches, {len(todo)} to render "
          f"(ref centroid {ref_cent:.0f}Hz attack {ref_atk:.0f}ms)", flush=True)
    for i, (rel, p) in enumerate(todo):
        try:
            s = surgepy.createSurge(SR)
            s.loadPatch(str(p))
            y = render_phrase(s, phrase, dur)
            y = y * (10 ** (-6 / 20) / (np.abs(y).max() + 1e-9))
            scores[rel] = round(probe_distance(y, dur, ref_prof,
                                               ref_cent, ref_atk), 2)
        except Exception as e:                      # patch zoo: skip corrupt ones
            print(f"  skip {rel}: {e}", flush=True)
            scores[rel] = 999.0
        if (i + 1) % 25 == 0:
            cache_file.write_text(json.dumps(scores, indent=0))
            print(f"  {i + 1}/{len(todo)}", flush=True)
    cache_file.write_text(json.dumps(scores, indent=0))

    ranked = sorted((v, k) for k, v in scores.items()
                    if v < 999 and (not filters
                                    or any(f.lower() in k.lower() for f in filters)))
    print(f"\ntop matches for {tg.key}:")
    for v, k in ranked[:24]:
        print(f"  {v:6.2f}  {k}")
    print("\npaste-ready candidates:")
    for i, (v, k) in enumerate(ranked[:5]):
        rel = k.split(":", 1)[1]
        slugname = re.sub(r"[^A-Za-z0-9]+", "",
                          Path(rel).stem.lower())[:12]
        print(f'  {{ key = "{tg.short}{"abcde"[i]}-{slugname}", '
              f'base = "factory:{rel}", tweaks = [] }},')


# ----------------------------------------------------------------- project ---
def cmd_project(spec: AlbumSpec) -> None:
    scores = json.loads((spec.project_dir / "scores.json").read_text())
    by_t: dict[str, list[dict]] = {}
    for r in scores:
        by_t.setdefault(r["target"], []).append(r)
    for lst in by_t.values():
        lst.sort(key=lambda r: r["dist"])

    tracks = []
    for tg in spec.targets:
        ln = tg.t1 - tg.t0
        tracks.append(rpp.track(
            f"== {tg.short} · {tg.title} · REF mix", 0,
            rpp.wave_item(0, ln, f"{tg.key}-mix", f"refs/{tg.key}-mix.wav")))
        tracks.append(rpp.track(
            f"   {tg.short} · REF stem", 1,
            rpp.wave_item(0, ln, f"{tg.key}-stem", f"refs/{tg.key}-stem.wav")))
        for i, r in enumerate(by_t.get(tg.short, [])):
            star = " *BEST*" if i == 0 else ""
            tracks.append(rpp.track(
                f"   {tg.short} · {r['cand']} (d={r['dist']}){star}", 1,
                rpp.wave_item(0, tg.phrase_dur, r["cand"], f"renders/{r['cand']}.wav")))
        tracks.append(rpp.track(
            f"   {tg.short} · SURGE LIVE (patch {spec.collection}/{tg.short}*)", 1,
            rpp.phrase_item(tg.phrase, tg.phrase_dur, f"{tg.short} phrase")))
    for seg in spec.drums:
        seg_dir = spec.project_dir / "drums" / seg.tag
        if not (seg_dir / "pattern.json").exists():
            continue
        meta = json.loads((seg_dir / "pattern.json").read_text())
        dur = meta["t1"] - meta["t0"]
        rel = f"drums/{seg.tag}"
        tracks.append(rpp.track(
            f"== DRUMS {seg.tag} · REF stem ({meta['tempo']}bpm)", 0,
            rpp.wave_item(0, dur, f"{seg.tag}-ref", f"{rel}/ref-stem.wav")))
        tracks.append(rpp.track(
            f"   DRUMS {seg.tag} · rebuild", 1,
            rpp.wave_item(0, dur, f"{seg.tag}-rebuild", f"{rel}/rebuild.wav")))
        tracks.append(rpp.track(
            f"   DRUMS {seg.tag} · MIDI -> drumkv1 (kit {rel}/)", 1,
            rpp.drum_item(meta["hits"], dur, f"{seg.tag} pattern")))
    out = spec.project_dir / f"{spec.name}.rpp"
    out.write_text(rpp.project(tracks))
    print(f"wrote {out} ({len(tracks)} tracks)")


def main() -> None:
    spec = load(Path(sys.argv[1]))
    what = sys.argv[2] if len(sys.argv) > 2 else "all"
    if what == "browse":
        cmd_browse(spec, sys.argv[3:])
        return
    cmds = {"render": cmd_render, "project": cmd_project, "install": cmd_install}
    for name in (cmds if what == "all" else {what: cmds[what]}):
        cmds[name](spec)


if __name__ == "__main__":
    main()
