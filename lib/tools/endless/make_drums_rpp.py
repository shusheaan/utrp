"""Assemble endless-drums.rpp: per segment ref stem vs rebuild vs MIDI pattern."""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path.home() / "storage/daw/endless-ref"
DRUMS = BASE / "drums"
TICKS_PER_S = 1920  # 120 bpm project, 960 ticks/QN
GM_NOTE = {"kick": 36, "snare": 38, "hat": 42, "perc": 39}


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


def midi_item(hits: list[dict], dur: float, name: str) -> str:
    events = []
    for h in hits:
        note = GM_NOTE[h["cls"]]
        vel = max(1, min(127, int(h["vel"])))
        t0 = int(h["t"] * TICKS_PER_S)
        events.append((t0, 1, note, vel))
        events.append((t0 + int(0.12 * TICKS_PER_S), 0, note, 0))
    events.sort(key=lambda e: (e[0], e[1]))
    lines, last = [], 0
    for tick, kind, note, vel in events:
        delta, last = tick - last, tick
        status = "90" if kind else "80"
        lines.append(f"        E {delta} {status} {note:02x} {vel:02x}")
    ev = "\n".join(lines)
    return f"""    <ITEM
      POSITION 0
      LENGTH {dur}
      NAME "{name}"
      <SOURCE MIDI
        HASDATA 1 960 QN
{ev}
        E {max(0, int(dur * TICKS_PER_S) - last)} b0 7b 00
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
    tracks = []
    for seg_dir in sorted(DRUMS.iterdir()):
        if not (seg_dir / "pattern.json").exists():
            continue
        meta = json.loads((seg_dir / "pattern.json").read_text())
        tag = seg_dir.name
        dur = meta["t1"] - meta["t0"]
        bpm = meta["tempo"]
        rel = f"drums/{tag}"
        tracks.append(track(f"== {tag} · REF drum-stem ({bpm}bpm)", 0,
                            wave_item(0, dur, f"{tag}-ref", f"{rel}/ref-stem.wav")))
        tracks.append(track(f"   {tag} · rebuild (sampled one-shots)", 1,
                            wave_item(0, dur, f"{tag}-rebuild", f"{rel}/rebuild.wav")))
        tracks.append(track(f"   {tag} · MIDI pattern -> drumkv1 (kit: {rel}/)", 1,
                            midi_item(meta["hits"], dur, f"{tag} pattern")))
    rpp = ('<REAPER_PROJECT 0.1 "7.78/linux-x86_64" 1754700001\n'
           "  TEMPO 120 4 4\n" + "".join(tracks) + ">\n")
    out = BASE / "endless-drums.rpp"
    out.write_text(rpp)
    print(f"wrote {out} with {len(tracks)} tracks")


if __name__ == "__main__":
    main()
