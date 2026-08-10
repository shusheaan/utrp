"""Assemble the endless-ref REAPER project (text .rpp) in ~/storage/daw/endless-ref."""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path.home() / "storage/daw/endless-ref"
SCORES = Path(__file__).parent / "render-scores.json"

TICKS_PER_S = 1920  # 120 bpm, 960 ticks per QN

# (t, note, vel, dur) phrases - keep in sync with render.py
def pulses(notes, t0, until, period, gate, vel):
    out = []
    t = t0
    while t < until:
        out += [(t, n, vel, gate) for n in notes]
        t += period
    return out


PHRASES = {
    "A": (13.0, [(0.2, n, 88, 9.0) for n in (45, 57, 60, 62, 64, 69)]),
    "B": (13.0, pulses([43, 58, 62, 67, 72], 0.2, 6.2, 0.25, 0.17, 105)
          + [(6.45, n, 105, 3.0) for n in (43, 58, 62, 67, 72)]),
    "C": (17.0, [(0.2, n, 92, 12.0) for n in (35, 54, 59, 64)]),
    "D": (11.0, pulses([48, 55, 60, 63, 67, 70], 0.2, 6.2, 0.75, 0.55, 96)),
}

REF_LAYOUT = {  # target -> list of (wav base name, position, length)
    "A": [("A-atyourbest-intro", 0, 16), ("A-atyourbest-verse", 18, 30),
          ("A-atyourbest-outro", 50, 26)],
    "B": [("B-mitsubushi-chords", 0, 41), ("B-mitsubushi-filtered", 43, 35)],
    "C": [("C-impietas-drone", 0, 32)],
    "D": [("D-hublots-lead", 0, 60)],
}
TITLES = {
    "A": "At Your Best pad", "B": "Mitsubushi saw chords",
    "C": "Impietas drone", "D": "Hublots keys",
}
SKIP = {"A2b-fmpad-dark", "D2b-dxep-dark"}


def wave_item(pos: float, length: float, name: str, file: str) -> str:
    return f"""    <ITEM
      POSITION {pos}
      LENGTH {length}
      NAME "{name}"
      <SOURCE WAVE
        FILE "{file}"
      >
    >
"""


def midi_item(target: str) -> str:
    dur, phrase = PHRASES[target]
    events = []
    for t, note, vel, d in phrase:
        events.append((int(t * TICKS_PER_S), 1, note, vel))
        events.append((int((t + d) * TICKS_PER_S), 0, note, 0))
    events.sort(key=lambda e: (e[0], e[1]))  # offs before ons at same tick
    lines, last = [], 0
    for tick, kind, note, vel in events:
        delta, last = tick - last, tick
        status = "90" if kind else "80"
        lines.append(f"        E {delta} {status} {note:02x} {vel:02x}")
    ev = "\n".join(lines)
    return f"""    <ITEM
      POSITION 0
      LENGTH {dur}
      NAME "{target} phrase"
      <SOURCE MIDI
        HASDATA 1 960 QN
{ev}
        E {int(dur * TICKS_PER_S) - last} b0 7b 00
      >
    >
"""


def track(name: str, muted: int, items: str) -> str:
    return f"""  <TRACK
    NAME "{name}"
    MUTESOLO {muted} 0 0
{items}  >
"""


def main() -> None:
    scores = {r["cand"]: r for r in json.loads(SCORES.read_text())}
    by_target: dict[str, list[dict]] = {}
    for r in scores.values():
        if r["cand"] in SKIP:
            continue
        by_target.setdefault(r["target"], []).append(r)
    for lst in by_target.values():
        lst.sort(key=lambda r: r["dist"])

    tracks = []
    for tgt in "ABCD":
        title = TITLES[tgt]
        mix = "".join(wave_item(p, ln, f"{n}-mix", f"refs/{n}-mix.wav")
                      for n, p, ln in REF_LAYOUT[tgt])
        stem = "".join(wave_item(p, ln, f"{n}-stem", f"refs/{n}-stem.wav")
                       for n, p, ln in REF_LAYOUT[tgt])
        tracks.append(track(f"== {tgt} · {title} · REF mix", 0, mix))
        tracks.append(track(f"   {tgt} · REF synth-stem", 1, stem))
        for i, r in enumerate(by_target.get(tgt, [])):
            star = " *BEST*" if i == 0 else ""
            item = wave_item(0, PHRASES[tgt][0], r["cand"], f"renders/{r['cand']}.wav")
            tracks.append(track(f"   {tgt} · {r['cand']} (d={r['dist']}){star}", 1, item))
        tracks.append(track(f"   {tgt} · SURGE LIVE (load patch Endless/{tgt}*)", 1,
                            midi_item(tgt)))

    rpp = ('<REAPER_PROJECT 0.1 "7.78/linux-x86_64" 1754700000\n'
           "  TEMPO 120 4 4\n" + "".join(tracks) + ">\n")
    out = BASE / "endless-ref.rpp"
    out.write_text(rpp)
    print(f"wrote {out} with {len(tracks)} tracks")


if __name__ == "__main__":
    main()
