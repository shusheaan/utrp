"""Text builders for REAPER .rpp projects (pure string functions)."""
from __future__ import annotations

TICKS_PER_S = 1920  # 120 bpm project, 960 ticks per QN
GM_NOTE = {"kick": 36, "snare": 38, "hat": 42, "perc": 39}


def wave_item(pos: float, length: float, name: str, file: str) -> str:
    return (f'    <ITEM\n      POSITION {pos}\n      LENGTH {length}\n'
            f'      NAME "{name}"\n      <SOURCE WAVE\n        FILE "{file}"\n'
            f'      >\n    >\n')


def track(name: str, muted: int, items: str) -> str:
    return f'  <TRACK\n    NAME "{name}"\n    MUTESOLO {muted} 0 0\n{items}  >\n'


def _midi_item(events: list[tuple[int, int, int, int]], dur: float, name: str) -> str:
    events.sort(key=lambda e: (e[0], e[1]))
    lines, last = [], 0
    for tick, kind, note, vel in events:
        delta, last = tick - last, tick
        lines.append(f"        E {delta} {'90' if kind else '80'} {note:02x} {vel:02x}")
    ev = "\n".join(lines)
    return (f'    <ITEM\n      POSITION 0\n      LENGTH {dur}\n      NAME "{name}"\n'
            f'      <SOURCE MIDI\n        HASDATA 1 960 QN\n{ev}\n'
            f'        E {max(0, int(dur * TICKS_PER_S) - last)} b0 7b 00\n'
            f'      >\n    >\n')


def phrase_item(phrase, dur: float, name: str) -> str:
    events = []
    for ev in phrase:
        t0 = int(ev.t * TICKS_PER_S)
        events.append((t0, 1, ev.note, ev.vel))
        events.append((t0 + int(ev.dur * TICKS_PER_S), 0, ev.note, 0))
    return _midi_item(events, dur, name)


def drum_item(hits: list[dict], dur: float, name: str) -> str:
    events = []
    for h in hits:
        note = GM_NOTE[h["cls"]]
        t0 = int(h["t"] * TICKS_PER_S)
        events.append((t0, 1, note, max(1, min(127, int(h["vel"])))))
        events.append((t0 + int(0.12 * TICKS_PER_S), 0, note, 0))
    return _midi_item(events, dur, name)


def project(tracks: list[str]) -> str:
    return ('<REAPER_PROJECT 0.1 "7.78/linux-x86_64" 1754700000\n'
            "  TEMPO 120 4 4\n" + "".join(tracks) + ">\n")
