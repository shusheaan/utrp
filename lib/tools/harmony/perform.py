"""Perform a utrp-simulated progression through lib timbres (surgepy venv).

End-to-end chain: session.yaml -> utrp-sim binary (the shared Rust progression
engine, exposed through lib/tools/simulate) -> pad chords + a modular-style
ornament layer (euclidean clock x Turing-machine shift register, quantized to
the sounding chord) -> one continuous 2-instrument Surge stream -> speakers
(paplay) or offline wav, plus a 2-track MIDI + JSON log for the DAW.

Usage:
  python perform.py session.yaml           # live playback (Ctrl-C stops)
  python perform.py session.yaml --wav     # offline render, full length
"""
from __future__ import annotations

import json
import random
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))
import smf  # noqa: E402
from explore import HARMONY_DIR, LIB, SR, Sound  # noqa: E402

SIM_BIN = Path(__file__).parents[1] / "simulate/target/release/utrp-sim"
PPQ = 480


# -------------------------------------------------------------- simulation ---
def run_sim(cfg: dict) -> list[dict]:
    if not SIM_BIN.exists():
        raise SystemExit(
            f"{SIM_BIN} missing — build it once:\n"
            f"  cargo build --release --manifest-path {SIM_BIN.parents[2]}/Cargo.toml")
    cmd = [str(SIM_BIN)]
    for k in ("measures", "threshold", "difficulty", "base", "key", "mode"):
        if k in cfg:
            cmd += [f"--{k}", str(cfg[k])]
    if cfg.get("seed") is not None:
        cmd += ["--seed", str(cfg["seed"])]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


# --------------------------------------------------------- ornament engine ---
def euclid(k: int, n: int, rotate: int = 0) -> list[bool]:
    """Bjorklund pattern: k pulses spread as evenly as possible over n steps."""
    pat = [(i * k) % n < k for i in range(n)]
    return pat[rotate % n:] + pat[:rotate % n]


@dataclass
class Turing:
    """Shift-register melody: loops its window, mutates with probability."""
    register: list[int]
    rng: random.Random
    mutate: float
    pos: int = 0

    def step(self, pool: list[int]) -> int:
        i = self.pos % len(self.register)
        if self.register[i] == 0 or self.rng.random() < self.mutate:
            self.register[i] = self.rng.choice(pool)      # 0 = uninitialized
        self.pos += 1
        # re-quantize a held slot to the current pool (chord may have changed)
        if self.register[i] not in pool:
            self.register[i] = min(pool, key=lambda p: abs(p - self.register[i]))
        return self.register[i]


def pitch_pool(cfg: dict, chord_notes: list[int], scale: list[int],
               root_pc: int | None = None) -> list[int]:
    lo, hi = cfg["register"]
    kind = cfg.get("pool", "chord")
    pcs = sorted({n % 12 for n in chord_notes})
    if kind == "scale":
        pcs = sorted(set(scale))
    elif kind == "chord+9":
        if root_pc is None or not 0 <= root_pc < 12:
            raise ValueError("chord+9 requires explicit root_pc (legacy replay needs migration)")
        pcs = sorted(set(pcs) | {(root_pc + 2) % 12})
    return [n for n in range(lo, hi + 1) if n % 12 in pcs]


def octave_up_in_register(note: int, upper: int) -> int:
    """Never clamp to a different pitch class at the register boundary."""
    return note + 12 if note + 12 <= upper else note


# ------------------------------------------------------------------ player ---
class Player:
    """Sample-scheduled continuous render over several Surge instances."""

    def __init__(self, sounds: list[Sound], sink) -> None:
        self.sounds = sounds
        self.sink = sink
        self.events: list[tuple[int, bool, int, int, int]] = []  # smp,on,inst,note,vel
        self.pos = 0

    def schedule(self, at_s: float, on: bool, inst: int, note: int, vel: int) -> None:
        self.events.append((int(at_s * SR), on, inst, note, vel))

    def run_until(self, t_s: float) -> None:
        self.events.sort()
        bs = self.sounds[0].surge.getBlockSize()
        end = int(t_s * SR)
        while self.pos < end:
            nxt = self.events[0][0] if self.events else end
            stop = min(max(nxt, self.pos + bs), end)
            nblocks = max(1, (stop - self.pos) // bs)
            mix: np.ndarray | None = None
            for snd in self.sounds:
                buf = snd.surge.createMultiBlock(nblocks)
                snd.surge.processMultiBlock(buf, 0, nblocks)
                mix = buf if mix is None else mix + buf
            assert mix is not None
            self.sink(np.ascontiguousarray(mix.T, dtype=np.float32))
            self.pos += nblocks * bs
            while self.events and self.events[0][0] <= self.pos:
                _, on, inst, note, vel = self.events.pop(0)
                s = self.sounds[inst].surge
                if on:
                    s.playNote(0, note, vel, 0)
                else:
                    s.releaseNote(0, note, 0)


# ---------------------------------------------------------------- schedule ---
def schedule_session(cfg: dict, measures: list[dict], player: Player,
                     midi: dict[str, list[smf.Event]], log: list[dict]) -> float:
    pf, orn = cfg["perform"], cfg.get("ornament", {})
    rng = random.Random(orn.get("seed"))
    step_s = float(pf["step_s"])
    beat_s = step_s / 4
    turing = Turing(register=[0] * int(orn.get("turing", {}).get("length", 8)),
                    rng=rng,
                    mutate=float(orn.get("turing", {}).get("mutate", 0.15)))
    gates = euclid(*orn.get("euclid", [5, 16, 0])) if orn.get("enabled") else []

    def tick(t: float) -> int:
        return int(t / beat_s * PPQ)

    t = 0.5
    for meas in measures:
        slots = meas["chords"]
        slot_s = step_s / len(slots)
        for chord in slots:
            notes = [int(n) for n in chord["notes"]]
            strum = 0.0
            off_t = t + slot_s * rng.uniform(*pf.get("overlap", [1.05, 1.3]))
            for n in notes:
                vel = rng.randrange(*pf.get("pad_vel", [66, 90]))
                player.schedule(t + strum, True, 0, n, vel)
                player.schedule(off_t, False, 0, n, 0)
                midi["pad"] += [(tick(t + strum), True, 0, n, vel),
                                (tick(t + slot_s), False, 0, n, 0)]
                strum += rng.uniform(*pf.get("strum_s", [0.015, 0.06]))
            log.append({"t": round(t, 2), "key": meas["key"],
                        "modulation": meas["modulation"],
                        "role": chord["role"], "symbol": chord["symbol"],
                        "notes": notes})
            if orn.get("enabled"):
                pool = pitch_pool(orn, notes, meas["scale"], chord.get("root_pc"))
                if not pool:
                    raise ValueError("ornament register contains no allowed notes")
                n_steps = max(1, int(slot_s / beat_s * orn.get("steps_per_beat", 2)))
                sub = slot_s / n_steps
                for i in range(n_steps):
                    gi = int((t + i * sub) / (beat_s / orn.get("steps_per_beat", 2)))
                    if not gates[gi % len(gates)] or \
                            rng.random() > orn.get("density", 0.75):
                        continue
                    p = turing.step(pool)
                    if rng.random() < orn.get("octave_leap", 0.08):
                        p = octave_up_in_register(p, orn["register"][1])
                    vel = rng.randrange(*orn.get("vel", [38, 74]))
                    t0 = t + i * sub
                    dur = sub * float(orn.get("gate", 0.5))
                    player.schedule(t0, True, 1, p, vel)
                    player.schedule(t0 + dur, False, 1, p, 0)
                    midi["ornament"] += [(tick(t0), True, 1, p, vel),
                                         (tick(t0 + dur), False, 1, p, 0)]
            t += slot_s
            player.run_until(t)
    return t


# --------------------------------------------------------------------- run ---
def main() -> None:
    cfg = yaml.safe_load(Path(sys.argv[1]).read_text())
    offline = "--wav" in sys.argv
    name = str(cfg.get("out", {}).get("name", "session"))
    sim_log = Path(__file__).parent / "progressions" / f"{name}-sim.json"
    if "--replay" in sys.argv:
        measures = json.loads(sim_log.read_text())
        print(f"replaying {sim_log}")
    else:
        measures = run_sim(cfg.get("sim", {}))
        sim_log.parent.mkdir(exist_ok=True)
        sim_log.write_text(json.dumps(measures, indent=1))
    pf, orn = cfg["perform"], cfg.get("ornament", {})

    sounds = [Sound(LIB / "surge" / pf["pad_patch"])]
    if orn.get("enabled"):
        sounds.append(Sound(LIB / "surge" / orn["patch"]))

    chunks: list[np.ndarray] = []
    proc: subprocess.Popen | None = None
    if offline:
        sink = chunks.append
    else:
        proc = subprocess.Popen(
            ["paplay", "--raw", f"--rate={SR}", "--channels=2",
             "--format=float32le", "/dev/stdin"], stdin=subprocess.PIPE)
        assert proc.stdin is not None
        sink = lambda a: proc.stdin.write(a.tobytes())  # noqa: E731

    player = Player(sounds, sink)
    midi: dict[str, list[smf.Event]] = {"pad": [], "ornament": []}
    log: list[dict] = []
    n = len(measures)
    print(f"{n} measures x {pf['step_s']}s = {n * pf['step_s'] / 60:.1f} min | "
          f"pad {pf['pad_patch']}"
          + (f" | orn {orn['patch']}" if orn.get("enabled") else ""))
    try:
        end = schedule_session(cfg, measures, player, midi, log)
        player.run_until(end + 4.0)
    except (KeyboardInterrupt, BrokenPipeError):
        print("\nstopped")
    finally:
        if proc and proc.stdin:
            proc.stdin.close()
            proc.wait()

    for row in log:
        print(f"{row['t']:7.1f}s  {row['key']:18s} {row['role']:8s} "
              f"{row['symbol']}")

    HARMONY_DIR.mkdir(parents=True, exist_ok=True)
    bpm = 240.0 / float(pf["step_s"])
    tracks = [smf.track_bytes([], name=name, tempo_bpm=bpm),
              smf.track_bytes(midi["pad"], name="pad")]
    if midi["ornament"]:
        tracks.append(smf.track_bytes(midi["ornament"], name="ornament"))
    (HARMONY_DIR / f"{name}.mid").write_bytes(smf.file_bytes(tracks, ppq=PPQ))
    (Path(__file__).parent / "progressions" / f"{name}.json").write_text(
        json.dumps(log, indent=1, ensure_ascii=False))
    if offline:
        y = np.concatenate(chunks)
        y *= 10 ** (-8 / 20) / (np.abs(y).max() + 1e-9)
        sf.write(HARMONY_DIR / f"{name}.wav", y, SR)
        print(f"wav: {HARMONY_DIR / f'{name}.wav'}")
    print(f"mid: {HARMONY_DIR / f'{name}.mid'}  log: progressions/{name}.json")


if __name__ == "__main__":
    main()
