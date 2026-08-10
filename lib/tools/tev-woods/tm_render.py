"""Tev Woods + MAGDALENE: render candidates, score, assemble both projects."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import soundfile as sf
import surgepy

import sys
sys.path.insert(0, str(Path(__file__).parent))
import render as R  # noqa: E402
from render import NoteEv, hold, walk_params, set_by_display  # noqa: E402

BASE = Path(__file__).parent
FACT = Path("/usr/share/surge-xt")
LIB = Path.home() / "work/utrp/lib/surge"
TICKS_PER_S = 1920
GM_NOTE = {"kick": 36, "snare": 38, "hat": 42, "perc": 39}

ALBUMS = {
    "tev-woods": {
        "refs_dir": BASE / "tev-targets",
        "phrases": {
            "T1": (14.0, hold([48, 55, 60, 64, 69, 74], 0.2, 10.0, 86)),
            "T2": (14.0, [NoteEv(0.3, 65, 84, 2.2), NoteEv(2.8, 72, 88, 2.2),
                          NoteEv(5.4, 77, 92, 3.2), NoteEv(9.0, 75, 86, 1.8),
                          NoteEv(11.0, 72, 84, 2.0)]),
            "T3": (12.0, [NoteEv(0.2, 31, 110, 2.0), NoteEv(2.4, 31, 110, 1.4),
                          NoteEv(4.0, 34, 106, 1.8), NoteEv(6.0, 29, 108, 1.8),
                          NoteEv(8.0, 31, 110, 3.0)]),
        },
        "ref_specs": {
            "T1": ("T1-ffh-pad-stem.wav", 2.0, 34.0),
            "T2": ("T2-bts-lead-stem.wav", 2.0, 44.0),
            "T3": ("T3-bts-sub-stem.wav", 2.0, 44.0),
        },
        "cands": (
            ("T1a-bright", "T1", FACT / "patches_factory/Pads/Bright.fxp",
             (("Amp EG Attack", "0.90 s"), ("Osc Drift", "40.00 %"))),
            ("T1b-stringmachine", "T1", FACT / "patches_3rdparty/Jacky Ligon/Pads/String Machine 11.fxp",
             (("Amp EG Attack", "0.90 s"), ("Osc Drift", "40.00 %"))),
            ("T1c-mks70", "T1", FACT / "patches_factory/Pads/MKS-70 Warm Pad.fxp",
             (("Amp EG Attack", "0.90 s"), ("Osc Drift", "40.00 %"))),
            ("T2a-classiclead", "T2", FACT / "patches_factory/Leads/Classic Lead 1.fxp",
             (("Amp EG Attack", "0.70 s"),)),
            ("T2b-cyberflute", "T2", FACT / "patches_factory/Winds/Cyber Flute.fxp",
             (("Amp EG Attack", "0.70 s"),)),
            ("T2c-low", "T2", FACT / "patches_factory/Winds/Low.fxp",
             (("Amp EG Attack", "0.70 s"),)),
            ("T3a-deepend", "T3", FACT / "patches_factory/Basses/Deep End.fxp",
             (("Amp EG Attack", "0.12 s"),)),
            ("T3b-bass1", "T3", FACT / "patches_factory/Basses/Bass 1.fxp",
             (("Amp EG Attack", "0.12 s"),)),
            ("T3c-ebass", "T3", FACT / "patches_factory/Basses/E-Bass.fxp",
             (("Amp EG Attack", "0.12 s"),)),
        ),
        "ref_cuts": {"T1": ("T1-ffh-pad", 36.0), "T2": ("T2-bts-lead", 46.0),
                     "T3": ("T3-bts-sub", 46.0)},
        "titles": {"T1": "Far from Home pad", "T2": "Back to See lead",
                   "T3": "Back to See sub"},
        "drums": ["walls", "lostintime"],
    },
    "magdalene": {
        "refs_dir": BASE / "magda-targets",
        "phrases": {
            "M1": (17.0, hold([38, 46, 53, 60, 65], 0.2, 13.0, 88)),
            "M2": (14.0, hold([41, 55, 60, 64, 69, 74], 0.2, 10.0, 86)),
            "M3": (16.0, hold([40, 48, 55, 59, 62, 67, 71], 0.2, 12.0, 84)),
            "M4": (12.0, [NoteEv(t, n, 112, 0.32)
                          for t in (0.3, 1.5, 2.7, 3.6, 4.8, 6.0, 7.2)
                          for n in (50, 57, 64, 66, 71)]),
        },
        "ref_specs": {
            "M1": ("M1-teyes-drone-stem.wav", 2.0, 68.0),
            "M2": ("M2-hwy-wash-stem.wav", 2.0, 48.0),
            "M3": ("M3-daybed-haze-stem.wav", 2.0, 58.0),
            "M4": ("M4-falien-stab-stem.wav", 2.0, 28.0),
        },
        "cands": (
            ("M1a-darkdrone", "M1", LIB / "endless/C4-darkdrone.fxp", ()),
            ("M1b-ghostpad", "M1", FACT / "patches_factory/Pads/Ghost Pad.fxp",
             (("Amp EG Attack", "0.75 s"),)),
            ("M1c-moody", "M1", FACT / "patches_factory/Pads/Moody Statement.fxp",
             (("Amp EG Attack", "0.75 s"),)),
            ("M2a-juno60", "M2", FACT / "patches_factory/Polysynths/Juno-60 Strings.fxp",
             (("Amp EG Attack", "0.40 s"),)),
            ("M2b-stringmachine", "M2", FACT / "patches_3rdparty/Jacky Ligon/Pads/String Machine 11.fxp",
             (("Amp EG Attack", "0.40 s"),)),
            ("M2c-mks70", "M2", FACT / "patches_factory/Pads/MKS-70 Warm Pad.fxp",
             (("Amp EG Attack", "0.40 s"),)),
            ("M3a-manaquest", "M3", FACT / "patches_3rdparty/Altenberg/Pads/Mana Quest.fxp",
             (("Amp EG Attack", "0.50 s"), ("Osc Drift", "45.00 %"))),
            ("M3b-moire", "M3", FACT / "patches_3rdparty/Jacky Ligon/Soundscapes/Moire 1.fxp",
             (("Osc Drift", "45.00 %"),)),
            ("M3c-distant", "M3", FACT / "patches_factory/Pads/Distant.fxp",
             (("Amp EG Attack", "0.50 s"), ("Osc Drift", "45.00 %"))),
            ("M4a-boss", "M4", FACT / "patches_factory/Polysynths/Boss.fxp",
             (("Amp EG Attack", "5.0 ms"), ("Amp EG Release", "0.40 s"))),
            ("M4b-1804", "M4", FACT / "patches_factory/Polysynths/1804.fxp",
             (("Amp EG Attack", "5.0 ms"), ("Amp EG Release", "0.40 s"))),
            ("M4c-doomsday", "M4", FACT / "patches_factory/Basses/Doomsday.fxp",
             (("Amp EG Attack", "5.0 ms"), ("Amp EG Release", "0.40 s"))),
        ),
        "ref_cuts": {"M1": ("M1-teyes-drone", 70.0), "M2": ("M2-hwy-wash", 50.0),
                     "M3": ("M3-daybed-haze", 60.0), "M4": ("M4-falien-stab", 30.0)},
        "titles": {"M1": "thousand eyes drone", "M2": "home with you wash",
                   "M3": "daybed haze", "M4": "fallen alien stab"},
        "drums": ["falien"],
    },
}


def wave_item(pos, length, name, file):
    return (f'    <ITEM\n      POSITION {pos}\n      LENGTH {length}\n'
            f'      NAME "{name}"\n      <SOURCE WAVE\n        FILE "{file}"\n      >\n    >\n')


def track(name, muted, items):
    return f'  <TRACK\n    NAME "{name}"\n    MUTESOLO {muted} 0 0\n{items}  >\n'


def midi_from_events(events, dur, name):
    events.sort(key=lambda e: (e[0], e[1]))
    lines, last = [], 0
    for tick, kind, note, vel in events:
        delta, last = tick - last, tick
        lines.append(f"        E {delta} {'90' if kind else '80'} {note:02x} {vel:02x}")
    ev = "\n".join(lines)
    return (f'    <ITEM\n      POSITION 0\n      LENGTH {dur}\n      NAME "{name}"\n'
            f'      <SOURCE MIDI\n        HASDATA 1 960 QN\n{ev}\n'
            f'        E {max(0, int(dur * TICKS_PER_S) - last)} b0 7b 00\n      >\n    >\n')


def phrase_midi(phrase, dur, name):
    events = []
    for ev in phrase:
        t0 = int(ev.t * TICKS_PER_S)
        events.append((t0, 1, ev.note, ev.vel))
        events.append((t0 + int(ev.dur * TICKS_PER_S), 0, ev.note, 0))
    return midi_from_events(events, dur, name)


def drum_midi(hits, dur, name):
    events = []
    for h in hits:
        note = GM_NOTE[h["cls"]]
        t0 = int(h["t"] * TICKS_PER_S)
        events.append((t0, 1, note, max(1, min(127, int(h["vel"])))))
        events.append((t0 + int(0.12 * TICKS_PER_S), 0, note, 0))
    return midi_from_events(events, dur, name)


def main() -> None:
    for album, cfg in ALBUMS.items():
        proj = Path.home() / "storage/daw" / album
        (proj / "refs").mkdir(parents=True, exist_ok=True)
        (proj / "renders").mkdir(exist_ok=True)
        for f in cfg["refs_dir"].glob("*.wav"):
            (proj / "refs" / f.name).write_bytes(f.read_bytes())

        fxp_out = BASE / f"{album}-patches"
        fxp_out.mkdir(exist_ok=True)
        ref_profiles = {}
        for tgt, (fname, t0, t1) in cfg["ref_specs"].items():
            y, sr = sf.read(cfg["refs_dir"] / fname, dtype="float32")
            ref_profiles[tgt] = R.band_profile(y[int(t0 * sr): int(t1 * sr)], sr)

        results = []
        for key, tgt, base, tweaks in cfg["cands"]:
            s = surgepy.createSurge(R.SR)
            s.loadPatch(str(base))
            params: dict = {}
            walk_params(s.getPatch(), params)
            applied = []
            for substr, disp in tweaks:
                hits = [k for k in params if substr in k and k.startswith("A ")]
                hits = hits or [k for k in params if substr in k]
                if hits and set_by_display(s, params[hits[0]], disp):
                    applied.append(substr)
            dur, phrase = cfg["phrases"][tgt]
            y = R.render(s, phrase, dur)
            peak = np.abs(y).max() + 1e-9
            y = y * (10 ** (-6 / 20) / peak)
            sf.write(proj / "renders" / f"{key}.wav", y, R.SR)
            body = y[int(1.5 * R.SR): int((dur - 2.5) * R.SR)]
            dist = R.spectral_distance(R.band_profile(body, R.SR), ref_profiles[tgt])
            s.savePatch(str(fxp_out / f"{key}.fxp"))
            results.append({"cand": key, "target": tgt, "base": str(base),
                            "dist": round(dist, 2), "tweaks": applied})
            print(f"{album[:4]} {key:20s} dist={dist:6.2f}", flush=True)
        (BASE / f"{album}-scores.json").write_text(json.dumps(results, indent=1))

        by_t: dict[str, list[dict]] = {}
        for r in results:
            by_t.setdefault(r["target"], []).append(r)
        for lst in by_t.values():
            lst.sort(key=lambda r: r["dist"])

        tracks = []
        for tgt in sorted(cfg["titles"]):
            name, ln = cfg["ref_cuts"][tgt]
            tracks.append(track(f"== {tgt} · {cfg['titles'][tgt]} · REF mix", 0,
                                wave_item(0, ln, f"{name}-mix", f"refs/{name}-mix.wav")))
            tracks.append(track(f"   {tgt} · REF stem", 1,
                                wave_item(0, ln, f"{name}-stem", f"refs/{name}-stem.wav")))
            for i, r in enumerate(by_t.get(tgt, [])):
                star = " *BEST*" if i == 0 else ""
                dur = cfg["phrases"][tgt][0]
                tracks.append(track(f"   {tgt} · {r['cand']} (d={r['dist']}){star}", 1,
                                    wave_item(0, dur, r["cand"], f"renders/{r['cand']}.wav")))
            dur, phrase = cfg["phrases"][tgt]
            tracks.append(track(f"   {tgt} · SURGE LIVE (patch {album}/{tgt}*)", 1,
                                phrase_midi(phrase, dur, f"{tgt} phrase")))
        # drums groups (pattern dirs produced by drums.py)
        for tag in cfg["drums"]:
            seg = proj / "drums" / tag
            if not (seg / "pattern.json").exists():
                continue
            meta = json.loads((seg / "pattern.json").read_text())
            dur = meta["t1"] - meta["t0"]
            rel = f"drums/{tag}"
            tracks.append(track(f"== DRUMS {tag} · REF stem ({meta['tempo']}bpm)", 0,
                                wave_item(0, dur, f"{tag}-ref", f"{rel}/ref-stem.wav")))
            tracks.append(track(f"   DRUMS {tag} · rebuild", 1,
                                wave_item(0, dur, f"{tag}-rebuild", f"{rel}/rebuild.wav")))
            tracks.append(track(f"   DRUMS {tag} · MIDI -> drumkv1 (kit {rel}/)", 1,
                                drum_midi(meta["hits"], dur, f"{tag} pattern")))
        rpp = ('<REAPER_PROJECT 0.1 "7.78/linux-x86_64" 1754700004\n'
               "  TEMPO 120 4 4\n" + "".join(tracks) + ">\n")
        (proj / f"{album}.rpp").write_text(rpp)
        print(f"wrote {proj / (album + '.rpp')} ({len(tracks)} tracks)")


if __name__ == "__main__":
    main()
