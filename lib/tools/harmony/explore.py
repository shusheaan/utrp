"""Chord/voicing explorer on the computer keyboard (surgepy venv).

Interactive:
  ~/.cache/timbre-pipeline/venv-render/bin/python explore.py [patch ...]
    a s d f g h j   diatonic seventh on degree 1-7 (current key/mode)
    A S D F G H J   secondary dominant V7/degree
    v / V           next / prev voicing     b  cycle family piano>guitar>all
    m               cycle mode              k / K  transpose key +1 / -1
    [ / ]           octave down / up        p / P  cycle patch
    space           replay last chord       r  record on/off   c  clear
    x               export progression (json -> progressions/, mid+wav -> daw)
    ?               help                    q  quit

Batch (also the smoke test):
  .../python explore.py demo <key> <mode> <patch> <token> ...
    token = [b|#]<degree>[quality][/voicing]   e.g. 2/drop2 5/rootless-b
            1maj7/pad-wide b6maj7/close        renders one wav + one mid
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import termios
import tomllib
import tty
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import soundfile as sf
import surgepy

sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))
import smf  # noqa: E402
from theory import (MODES, NOTE_NAMES, ChordSpec, altered_degree,  # noqa: E402
                    apply_voicing, diatonic_seventh, note_name,
                    secondary_dominant)

SR = 48000
LIB = Path(__file__).resolve().parents[2]               # .../utrp/lib
HARMONY_DIR = Path(os.environ.get("HARMONY_DIR",
                                  str(Path.home() / "storage/daw/harmony")))
DEGREE_KEYS = {"a": 1, "s": 2, "d": 3, "f": 4, "g": 5, "h": 6, "j": 7}
MODE_ORDER = tuple(MODES)


@dataclass(frozen=True)
class Voicing:
    name: str
    family: str
    qualities: frozenset[str]
    pattern: tuple[tuple[int, int], ...]

    def fits(self, quality: str) -> bool:
        return "*" in self.qualities or quality in self.qualities


@dataclass(frozen=True)
class Step:
    chord: ChordSpec
    voicing: str
    notes: tuple[int, ...]


def load_voicings() -> tuple[Voicing, ...]:
    out: list[Voicing] = []
    for name in ("voicings.toml", "voicings.local.toml"):
        p = Path(__file__).parent / name
        if not p.exists():
            continue
        for v in tomllib.loads(p.read_text())["voicing"]:
            out.append(Voicing(v["name"], v["family"],
                               frozenset(v["qualities"]),
                               tuple((int(d), int(o)) for d, o in v["pattern"])))
    if not out:
        raise SystemExit("no voicings.toml found")
    return tuple(out)


# ------------------------------------------------------------------ audio ---
class Sound:
    """One live Surge instance + a render cache + a paplay handle."""

    def __init__(self, patch: Path) -> None:
        self.patch = patch
        self.surge = surgepy.createSurge(SR)
        self.surge.loadPatch(str(patch))
        self.proc: subprocess.Popen | None = None
        (HARMONY_DIR / "cache").mkdir(parents=True, exist_ok=True)

    def load(self, patch: Path) -> None:
        self.patch = patch
        self.surge.loadPatch(str(patch))

    def render(self, notes: tuple[int, ...],
               hold: float = 2.4, tail: float = 1.4) -> np.ndarray:
        s = self.surge
        bs = s.getBlockSize()
        nb_hold, nb_tail = int(hold * SR / bs), int(tail * SR / bs)
        buf = s.createMultiBlock(nb_hold + nb_tail)
        for n in notes:
            s.playNote(0, n, 96, 0)
        s.processMultiBlock(buf, 0, nb_hold)
        for n in notes:
            s.releaseNote(0, n, 0)
        s.processMultiBlock(buf, nb_hold, nb_tail)
        y = buf.T
        return y * (10 ** (-8 / 20) / (np.abs(y).max() + 1e-9))

    def play(self, notes: tuple[int, ...]) -> None:
        wav = (HARMONY_DIR / "cache"
               / f"{self.patch.stem}-{'_'.join(map(str, notes))}.wav")
        if not wav.exists():
            sf.write(wav, self.render(notes), SR)
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
        self.proc = subprocess.Popen(["paplay", str(wav)],
                                     stderr=subprocess.DEVNULL)


# ------------------------------------------------------------------ state ---
@dataclass(frozen=True)
class State:
    key_pc: int = 5                       # F, ambient home base
    mode: str = "ionian"
    root_midi: int = 48                   # voicing origin octave
    family: str = "piano"
    vidx: int = 0
    pidx: int = 0
    recording: bool = False


def voicings_for(vs: tuple[Voicing, ...], st: State,
                 quality: str) -> list[Voicing]:
    pool = [v for v in vs if (st.family == "all" or v.family == st.family)
            and v.fits(quality)]
    return pool or [v for v in vs if v.fits(quality)]


def make_step(st: State, vs: tuple[Voicing, ...], chord: ChordSpec) -> Step:
    pool = voicings_for(vs, st, chord.quality)
    v = pool[st.vidx % len(pool)]
    return Step(chord, v.name, apply_voicing(chord, v.pattern, st.root_midi))


def describe(st: State, step: Step, patch: Path) -> str:
    names = " ".join(note_name(n) for n in step.notes)
    return (f"[{NOTE_NAMES[st.key_pc]} {st.mode}] "
            f"{step.chord.degree_label}: {step.chord.symbol():8s} "
            f"{step.voicing:14s} {names}   ({patch.parent.name}/{patch.stem})")


# ----------------------------------------------------------------- export ---
def export(prog: list[Step], name: str) -> None:
    prog_dir = Path(__file__).parent / "progressions"
    prog_dir.mkdir(exist_ok=True)
    (prog_dir / f"{name}.json").write_text(json.dumps([
        {"label": s.chord.degree_label, "symbol": s.chord.symbol(),
         "quality": s.chord.quality, "voicing": s.voicing,
         "notes": list(s.notes)} for s in prog], indent=1))
    events: list[smf.Event] = []
    for i, s in enumerate(prog):
        for n in s.notes:
            events.append((i * 4 * 480, True, 0, n, 90))
            events.append(((i * 4 + 4) * 480 - 30, False, 0, n, 0))
    HARMONY_DIR.mkdir(parents=True, exist_ok=True)
    (HARMONY_DIR / f"{name}.mid").write_bytes(smf.file_bytes([
        smf.track_bytes([], name=name, tempo_bpm=100),
        smf.track_bytes(events, name="chords")]))
    print(f"\nsaved {prog_dir / f'{name}.json'} + {HARMONY_DIR / f'{name}.mid'}")


def find_patches(args: list[str]) -> tuple[Path, ...]:
    if args:
        out = []
        for a in args:
            p = Path(a)
            out.append(p if p.exists() else LIB / "surge" / a)
        missing = [p for p in out if not p.exists()]
        if missing:
            raise SystemExit(f"patch not found: {missing}")
        return tuple(out)
    return tuple(sorted((LIB / "surge").rglob("*.fxp")))


# ------------------------------------------------------------------- demo ---
def parse_token(tok: str, st: State) -> tuple[ChordSpec, str | None]:
    acc = tok[0] if tok[0] in "b#" else ""
    body = tok[len(acc):]
    deg = int(body[0])
    rest = body[1:]
    quality, _, vname = rest.partition("/")
    if acc:
        chord = altered_degree(st.key_pc, acc, deg, quality or "maj7")
    elif quality:
        base = diatonic_seventh(st.key_pc, st.mode, deg)
        chord = ChordSpec(base.root_pc, quality, base.degree_label)
    else:
        chord = diatonic_seventh(st.key_pc, st.mode, deg)
    return chord, vname or None


def cmd_demo(args: list[str]) -> None:
    key, mode, patch_ref = args[0], args[1], args[2]
    st = State(key_pc=NOTE_NAMES.index(key), mode=mode)
    vs = load_voicings()
    snd = Sound(find_patches([patch_ref])[0])
    chunks, steps = [], []
    for tok in args[3:]:
        chord, vname = parse_token(tok, st)
        pool = voicings_for(vs, st, chord.quality)
        v = next((x for x in pool if x.name == vname), pool[0]) if vname \
            else pool[0]
        step = Step(chord, v.name, apply_voicing(chord, v.pattern, st.root_midi))
        steps.append(step)
        print(describe(st, step, snd.patch))
        chunks.append(snd.render(step.notes, hold=2.6, tail=0.4))
    HARMONY_DIR.mkdir(parents=True, exist_ok=True)
    name = f"demo-{key}-{mode}"
    sf.write(HARMONY_DIR / f"{name}.wav", np.concatenate(chunks), SR)
    export(steps, name)
    print(f"wav: {HARMONY_DIR / f'{name}.wav'}")


# ------------------------------------------------------------- interactive ---
def interact(patches: tuple[Path, ...]) -> None:
    vs = load_voicings()
    st = State()
    snd = Sound(patches[0])
    prog: list[Step] = []
    last: Step | None = None
    print(__doc__.split("Batch")[0])
    print(f"{len(patches)} patches, {len(vs)} voicings; first: {patches[0]}")
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    try:
        while True:
            ch = sys.stdin.read(1)
            if ch == "q":
                break
            elif ch in DEGREE_KEYS or ch.lower() in DEGREE_KEYS:
                deg = DEGREE_KEYS[ch.lower()]
                chord = (diatonic_seventh(st.key_pc, st.mode, deg) if ch.islower()
                         else secondary_dominant(st.key_pc, st.mode, deg))
                last = make_step(st, vs, chord)
                if st.recording:
                    prog.append(last)
                snd.play(last.notes)
                rec = f" ●{len(prog)}" if st.recording else ""
                print(describe(st, last, snd.patch) + rec)
            elif ch in "vV":
                st = replace(st, vidx=st.vidx + (1 if ch == "v" else -1))
                if last:
                    last = make_step(st, vs, last.chord)
                    snd.play(last.notes)
                    print(describe(st, last, snd.patch))
            elif ch == "b":
                order = ("piano", "guitar", "all")
                st = replace(st, family=order[(order.index(st.family) + 1) % 3],
                             vidx=0)
                print(f"family: {st.family}")
            elif ch == "m":
                st = replace(st, mode=MODE_ORDER[
                    (MODE_ORDER.index(st.mode) + 1) % len(MODE_ORDER)])
                print(f"mode: {NOTE_NAMES[st.key_pc]} {st.mode}")
            elif ch in "kK":
                d = 1 if ch == "k" else -1
                st = replace(st, key_pc=(st.key_pc + d) % 12,
                             root_midi=st.root_midi + d)
                print(f"key: {NOTE_NAMES[st.key_pc]} {st.mode}")
            elif ch in "[]":
                st = replace(st, root_midi=st.root_midi + (12 if ch == "]" else -12))
                print(f"octave root: {note_name(st.root_midi)}")
            elif ch in "pP":
                st = replace(st, pidx=(st.pidx + (1 if ch == "p" else -1))
                             % len(patches))
                snd.load(patches[st.pidx])
                print(f"patch: {patches[st.pidx].parent.name}/"
                      f"{patches[st.pidx].stem}")
            elif ch == " " and last:
                snd.play(last.notes)
            elif ch == "r":
                st = replace(st, recording=not st.recording)
                print(f"recording: {'ON' if st.recording else 'off'} "
                      f"({len(prog)} steps)")
            elif ch == "c":
                prog.clear()
                print("progression cleared")
            elif ch == "x" and prog:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                name = input("\nprogression name: ").strip() or "untitled"
                export(prog, name.replace(" ", "-"))
                tty.setcbreak(fd)
            elif ch == "?":
                print(__doc__.split("Batch")[0])
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        cmd_demo(sys.argv[2:])
    else:
        interact(find_patches(sys.argv[1:]))


if __name__ == "__main__":
    main()
