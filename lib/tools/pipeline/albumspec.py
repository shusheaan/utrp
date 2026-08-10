"""Album spec: frozen dataclasses + TOML loader.

One album = one TOML in specs/. Everything configurable lives there;
custom patch builders are deliberately unsupported (edit the fxp instead).
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

STORAGE_DAW = Path.home() / "storage/daw"
LIB_ROOT = Path(__file__).resolve().parents[2]          # .../utrp/lib
FACTORY = Path("/usr/share/surge-xt")
STEMS_DIR = Path(os.environ.get("STEMS_DIR", str(Path.home() / ".cache/demucs-stems")))


@dataclass(frozen=True)
class PhraseNote:
    t: float
    note: int
    vel: int
    dur: float


@dataclass(frozen=True)
class CandidateSpec:
    key: str                       # e.g. "S4b-manaquest"
    base: str                      # "factory:Pads/Bright.fxp" | "lib:endless/C4-darkdrone.fxp"
    tweaks: tuple[tuple[str, str], ...]  # (param-name substring, display value)

    def base_path(self) -> Path:
        kind, _, rel = self.base.partition(":")
        if kind == "factory":
            for sub in ("patches_factory", "patches_3rdparty"):
                p = FACTORY / sub / rel
                if p.exists():
                    return p
            raise FileNotFoundError(self.base)
        if kind == "lib":
            return LIB_ROOT / "surge" / rel
        raise ValueError(f"unknown base kind: {self.base}")


@dataclass(frozen=True)
class TargetSpec:
    key: str                       # e.g. "S1-pipe-wall"
    short: str                     # e.g. "S1"
    title: str
    track: str                     # flac filename without extension
    t0: float
    t1: float
    stem: str                      # demucs stem to measure against
    phrase: tuple[PhraseNote, ...]
    phrase_dur: float
    score_window: tuple[float, float]   # within the ref stem cut
    candidates: tuple[CandidateSpec, ...]


@dataclass(frozen=True)
class DrumSegSpec:
    tag: str
    track: str
    t0: float
    t1: float


@dataclass(frozen=True)
class AlbumSpec:
    name: str                      # storage project dir name
    collection: str                # lib/surge/<collection> patch dir
    album_dir: Path                # where the flacs live
    targets: tuple[TargetSpec, ...]
    drums: tuple[DrumSegSpec, ...]
    track_dirs: dict[str, Path] = field(default_factory=dict)  # per-track overrides

    @property
    def project_dir(self) -> Path:
        return STORAGE_DAW / self.name

    def flac(self, track: str) -> Path:
        return self.track_dirs.get(track, self.album_dir) / f"{track}.flac"

    def stems(self, track: str) -> Path:
        return STEMS_DIR / "htdemucs" / track


def _phrase(raw: dict) -> tuple[tuple[PhraseNote, ...], float]:
    dur = float(raw["dur"])
    notes: list[PhraseNote] = []
    if "hold" in raw:
        h = raw["hold"]
        notes += [PhraseNote(float(h.get("t0", 0.2)), int(n), int(h.get("vel", 88)),
                             float(h["len"])) for n in h["notes"]]
    for ev in raw.get("notes", []):
        notes.append(PhraseNote(float(ev[0]), int(ev[1]), int(ev[2]), float(ev[3])))
    if "pulses" in raw:
        p = raw["pulses"]
        t = float(p.get("t0", 0.2))
        while t < float(p["until"]):
            notes += [PhraseNote(t, int(n), int(p.get("vel", 100)), float(p["gate"]))
                      for n in p["notes"]]
            t += float(p["period"])
    if not notes:
        raise ValueError("phrase has no notes")
    return tuple(notes), dur


def load(path: Path) -> AlbumSpec:
    raw = tomllib.loads(path.read_text())
    targets = []
    for t in raw["targets"]:
        phrase, dur = _phrase(t["phrase"])
        cands = tuple(
            CandidateSpec(c["key"], c["base"],
                          tuple((a, b) for a, b in c.get("tweaks", [])))
            for c in t["candidates"])
        sw = t.get("score_window", [2.0, t["t1"] - t["t0"] - 2.0])
        targets.append(TargetSpec(
            key=t["key"], short=t["key"].split("-")[0], title=t["title"],
            track=t["track"], t0=float(t["t0"]), t1=float(t["t1"]),
            stem=t.get("stem", "other"), phrase=phrase, phrase_dur=dur,
            score_window=(float(sw[0]), float(sw[1])), candidates=cands))
    drums = tuple(DrumSegSpec(d["tag"], d["track"], float(d["t0"]), float(d["t1"]))
                  for d in raw.get("drums", []))
    return AlbumSpec(name=raw["album"]["name"],
                     collection=raw["album"].get("collection", raw["album"]["name"]),
                     album_dir=Path(raw["album"]["dir"]),
                     targets=tuple(targets), drums=drums,
                     track_dirs={k: Path(v) for k, v in
                                 raw["album"].get("track_dirs", {}).items()})
