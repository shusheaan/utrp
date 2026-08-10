"""Assemble sega-universe.rpp (run in .venv314: imports sega_render for phrases)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import sega_render as SR

BASE = Path(__file__).parent
PROJ = Path.home() / "storage/daw/sega-universe"
TICKS_PER_S = 1920

TITLES = {
    "S1": "Pipe warm wall", "S2": "Cradle swell",
    "S3": "Cradle soft lead (layer over S1 pad!)", "S4": "Universe shimmer wall",
}
REF_CUTS = {
    "S1": ("S1-pipe-wall", 40.0),
    "S2": ("S2-cradle-swell", 44.0),
    "S3": ("S3-cradle-lead", 42.0),
    "S4": ("S4-universe-shimmer", 75.0),
}


def wave_item(pos, length, name, file):
    return (f'    <ITEM\n      POSITION {pos}\n      LENGTH {length}\n'
            f'      NAME "{name}"\n      <SOURCE WAVE\n        FILE "{file}"\n      >\n    >\n')


def midi_item(target: str) -> str:
    dur, phrase = SR.PHRASES[target]
    events = []
    for ev in phrase:
        t0 = int(ev.t * TICKS_PER_S)
        events.append((t0, 1, ev.note, ev.vel))
        events.append((t0 + int(ev.dur * TICKS_PER_S), 0, ev.note, 0))
    events.sort(key=lambda e: (e[0], e[1]))
    lines, last = [], 0
    for tick, kind, note, vel in events:
        delta, last = tick - last, tick
        lines.append(f"        E {delta} {'90' if kind else '80'} {note:02x} {vel:02x}")
    ev = "\n".join(lines)
    return (f'    <ITEM\n      POSITION 0\n      LENGTH {dur}\n      NAME "{target} phrase"\n'
            f'      <SOURCE MIDI\n        HASDATA 1 960 QN\n{ev}\n'
            f'        E {max(0, int(dur * TICKS_PER_S) - last)} b0 7b 00\n      >\n    >\n')


def track(name, muted, items):
    return f'  <TRACK\n    NAME "{name}"\n    MUTESOLO {muted} 0 0\n{items}  >\n'


def main() -> None:
    (PROJ / "refs").mkdir(parents=True, exist_ok=True)
    for f in (BASE / "sega-targets").glob("*.wav"):
        shutil.copy(f, PROJ / "refs" / f.name)

    scores = json.loads((BASE / "sega-scores.json").read_text())
    by_target: dict[str, list[dict]] = {}
    for r in scores:
        by_target.setdefault(r["target"], []).append(r)
    for lst in by_target.values():
        lst.sort(key=lambda r: r["dist"])

    tracks = []
    for tgt in ("S1", "S2", "S3", "S4"):
        name, ln = REF_CUTS[tgt]
        tracks.append(track(f"== {tgt} · {TITLES[tgt]} · REF mix", 0,
                            wave_item(0, ln, f"{name}-mix", f"refs/{name}-mix.wav")))
        tracks.append(track(f"   {tgt} · REF synth-stem", 1,
                            wave_item(0, ln, f"{name}-stem", f"refs/{name}-stem.wav")))
        for i, r in enumerate(by_target.get(tgt, [])):
            star = " *BEST*" if i == 0 else ""
            dur = SR.PHRASES[tgt][0]
            tracks.append(track(f"   {tgt} · {r['cand']} (d={r['dist']}){star}", 1,
                                wave_item(0, dur, r["cand"], f"renders/{r['cand']}.wav")))
        tracks.append(track(f"   {tgt} · SURGE LIVE (load patch sega-universe/{tgt}*)", 1,
                            midi_item(tgt)))

    rpp = ('<REAPER_PROJECT 0.1 "7.78/linux-x86_64" 1754700003\n'
           "  TEMPO 120 4 4\n" + "".join(tracks) + ">\n")
    (PROJ / "sega-universe.rpp").write_text(rpp)
    print(f"wrote {PROJ / 'sega-universe.rpp'} with {len(tracks)} tracks")


if __name__ == "__main__":
    main()
