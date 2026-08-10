"""Drum pattern.json -> pattern.mid + grid.txt + grid.html (stdlib only).

Runs on any Python >= 3.11 (no numpy/librosa): quantizes detected hits onto
the beat grid (straight 16ths vs 8th triplets, per hit), writes a 3-track
SMF (tempo / quantized / as-played), an ASCII step grid and a self-contained
HTML grid. Requires pattern.json with "beats" (rerun `analysis.py <spec> drums`
if missing).

Usage:
  python drummidi.py <spec.toml> [tag ...]   # default: every segment in spec
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import smf  # noqa: E402
from albumspec import AlbumSpec, load  # noqa: E402

PPQ = 480
GM_NOTE = {"kick": 36, "snare": 38, "hat": 42, "perc": 39}
CLASSES = ("kick", "snare", "hat", "perc")
SUB16 = ("1", "e", "&", "a")


@dataclass(frozen=True)
class QHit:
    cls: str
    vel: int
    beat: float        # quantized position in beats from segment start
    raw_beat: float    # unquantized position in beats
    div: int           # 4 = straight 16th, 3 = 8th triplet
    dev_ms: float      # signed deviation from the chosen slot


# ------------------------------------------------------------------- grid ----
def fit_grid(hits: list[dict], beats: list[float]) -> tuple[float, float]:
    """Constant-tempo grid (origin, period) fitted to the hits.

    beat_track wobbles locally; these albums are sequenced at fixed tempo, so a
    two-parameter fit (period +-3%, phase) scored by velocity-weighted distance
    to the nearest 16th slot beats the raw beat times. Bar line = phase where
    kicks land on even beats and snares on odd ones.
    """
    if len(beats) < 2:
        raise ValueError("pattern.json lacks a usable beat grid; rerun drums step")
    diffs = sorted(b - a for a, b in zip(beats, beats[1:]))
    p0 = diffs[len(diffs) // 2]
    strong = [(float(h["t"]), int(h["vel"])) for h in hits if int(h["vel"]) >= 50]
    best = (-1.0, p0, 0.0)
    for dp in range(-30, 31):
        p = p0 * (1 + dp / 1000)
        for k in range(48):
            ph = k * p / 48
            score = 0.0
            for t, v in strong:
                frac = ((t - ph) / (p / 4)) % 1.0
                score += v * max(0.0, 1 - min(frac, 1 - frac) * 8)
            if score > best[0]:
                best = (score, p, ph)
    _, p, ph = best
    bar_score = [0.0] * 4
    for h in hits:
        b = round((float(h["t"]) - ph) / p)
        for off in range(4):
            even = (b - off) % 2 == 0
            if h["cls"] == "kick" and even:
                bar_score[off] += h["vel"]
            if h["cls"] == "snare" and not even:
                bar_score[off] += h["vel"]
    origin = ph + bar_score.index(max(bar_score)) * p
    while origin > 0:
        origin -= 4 * p
    return origin, p


def quantize(hits: list[dict], origin: float, period: float) -> list[QHit]:
    picked: dict[tuple[str, int], QHit] = {}
    for h in hits:
        bp = (float(h["t"]) - origin) / period
        i, frac = int(bp // 1), bp % 1.0
        err4 = abs(frac - round(frac * 4) / 4)
        err3 = abs(frac - round(frac * 3) / 3)
        div, q = (3, round(frac * 3) / 3) if err3 < 0.6 * err4 \
            else (4, round(frac * 4) / 4)
        qb = i + q
        qh = QHit(cls=str(h["cls"]), vel=int(h["vel"]), beat=qb, raw_beat=bp,
                  div=4 if q in (0.0, 1.0) else div,
                  dev_ms=(bp - qb) * period * 1000)
        key = (qh.cls, round(qb * 12))          # 12 = lcm slots per beat
        if key not in picked or qh.vel > picked[key].vel:
            picked[key] = qh
    return sorted(picked.values(), key=lambda q: (q.beat, q.cls))


# ------------------------------------------------------------------- midi ----
def write_midi(path: Path, tag: str, qhits: list[QHit], bpm: float) -> None:
    def events(attr: str) -> list[smf.Event]:
        ev: list[smf.Event] = []
        for q in qhits:
            tick = max(0, round(getattr(q, attr) * PPQ))
            ev.append((tick, True, 9, GM_NOTE[q.cls], q.vel))
            ev.append((tick + PPQ // 8, False, 9, GM_NOTE[q.cls], 0))
        return ev
    path.write_bytes(smf.file_bytes([
        smf.track_bytes([], name=tag, tempo_bpm=bpm),
        smf.track_bytes(events("beat"), name="quantized"),
        smf.track_bytes(events("raw_beat"), name="as played"),
    ], ppq=PPQ))


# ------------------------------------------------------------------- views ---
def _vel_char(vel: int) -> str:
    return "o" if vel < 52 else "O" if vel < 96 else "#"


def grid_text(tag: str, qhits: list[QHit], bpm: float, dur: float) -> str:
    n_bars = int(max(q.beat for q in qhits) // 4) + 1
    straight = [q for q in qhits if q.div == 4]
    trips = [q for q in qhits if q.div == 3]
    dev = sorted(abs(q.dev_ms) for q in qhits)
    lines = [f"== {tag}  {bpm} bpm  {dur:.1f}s  {n_bars} bars  "
             f"{len(qhits)} hits (straight {len(straight)} / triplet "
             f"{len(trips)})  |dev| med {dev[len(dev) // 2]:.1f}ms", ""]
    for bar in range(n_bars):
        lines.append(f"bar {bar + 1:02d} [" + " ".join(
            "".join(SUB16) for _ in range(4)) + "]")
        for cls in CLASSES:
            cells = ["·"] * 16
            for q in straight:
                if q.cls == cls and int(q.beat // 4) == bar:
                    cells[round((q.beat % 4) * 4) % 16] = _vel_char(q.vel)
            row = "|".join("".join(cells[b * 4:(b + 1) * 4]) for b in range(4))
            lines.append(f" {cls:5s} {row}")
        bar_trips = [q for q in trips if int(q.beat // 4) == bar]
        if bar_trips:
            lines.append(" trip  " + "  ".join(
                f"{q.cls}@{q.beat % 4 + 1:.2f}" for q in bar_trips))
        lines.append("")
    return "\n".join(lines)


HTML_HEAD = """<!doctype html><meta charset="utf-8"><title>{tag}</title><style>
body{{font:13px monospace;background:#14141a;color:#ccc;margin:1.5em}}
.bar{{margin-bottom:10px}} .lbl{{display:inline-block;width:52px;color:#888}}
.row{{white-space:nowrap}} h1{{font-size:15px;color:#eee}}
.c{{display:inline-block;width:17px;height:15px;margin:1px;border-radius:2px;
background:#26262e;vertical-align:middle}}
.c.b4{{margin-left:6px}} .t{{outline:2px solid #e6b34266}}
.kick{{background:#e05656}} .snare{{background:#56a8e0}}
.hat{{background:#5ee08a}} .perc{{background:#c47ae0}}
</style><h1>{tag} — {bpm} bpm, {nhits} hits</h1>
"""


def grid_html(tag: str, qhits: list[QHit], bpm: float) -> str:
    n_bars = int(max(q.beat for q in qhits) // 4) + 1
    out = [HTML_HEAD.format(tag=tag, bpm=bpm, nhits=len(qhits))]
    by_slot = {(q.cls, int(q.beat // 4), round((q.beat % 4) * 4)): q
               for q in qhits if q.div == 4}
    for bar in range(n_bars):
        out.append(f'<div class="bar"><div class="lbl">bar {bar + 1:02d}</div>')
        for cls in CLASSES:
            cells = []
            for s in range(16):
                q = by_slot.get((cls, bar, s))
                extra = f' b4' if s % 4 == 0 and s else ""
                if q is None:
                    cells.append(f'<span class="c{extra}"></span>')
                else:
                    cells.append(
                        f'<span class="c {cls}{extra}" style="opacity:'
                        f'{max(q.vel, 30) / 127:.2f}" title="{cls} vel {q.vel} '
                        f'dev {q.dev_ms:+.0f}ms"></span>')
            out.append(f'<div class="row"><span class="lbl">{cls}</span>'
                       + "".join(cells) + "</div>")
        trips = [q for q in qhits if q.div == 3 and int(q.beat // 4) == bar]
        if trips:
            out.append('<div class="row"><span class="lbl">trip</span>'
                       + "  ".join(f'<span class="t">{q.cls}@'
                                   f'{q.beat % 4 + 1:.2f}</span>' for q in trips)
                       + "</div>")
        out.append("</div>")
    return "\n".join(out)


# --------------------------------------------------------------------- cli ---
def run(spec: AlbumSpec, tags: list[str]) -> None:
    for seg in spec.drums:
        if tags and seg.tag not in tags:
            continue
        seg_dir = spec.project_dir / "drums" / seg.tag
        meta = json.loads((seg_dir / "pattern.json").read_text())
        if "beats" not in meta:
            raise SystemExit(f"{seg.tag}: no beats in pattern.json — rerun "
                             f"`analysis.py <spec> drums` first")
        dur = float(meta["t1"]) - float(meta["t0"])
        origin, period = fit_grid(meta["hits"],
                                  [float(b) for b in meta["beats"]])
        qhits = quantize(meta["hits"], origin, period)
        bpm = round(60.0 / period, 2)
        write_midi(seg_dir / "pattern.mid", seg.tag, qhits, bpm)
        txt = grid_text(seg.tag, qhits, bpm, dur)
        (seg_dir / "grid.txt").write_text(txt)
        (seg_dir / "grid.html").write_text(grid_html(seg.tag, qhits, bpm))
        print(txt.splitlines()[0])
        print(f"   -> {seg_dir}/pattern.mid + grid.txt + grid.html", flush=True)


def main() -> None:
    run(load(Path(sys.argv[1])), sys.argv[2:])


if __name__ == "__main__":
    main()
