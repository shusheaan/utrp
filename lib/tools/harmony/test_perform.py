"""Invariants for the perform layer + the utrp-sim binary contract.

Runs under pytest or plain python. The sim test is skipped if the glue
binary is not built yet.
"""
from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

from perform import SIM_BIN, Turing, euclid, pitch_pool


def test_euclid_known_patterns() -> None:
    assert euclid(3, 8) == [True, False, False, True, False, False, True, False]
    assert sum(euclid(5, 16)) == 5
    assert euclid(4, 4) == [True] * 4
    rot = euclid(3, 8, rotate=3)
    assert rot == [True, False, False, True, False, True, False, False]


def test_turing_loops_without_mutation() -> None:
    t = Turing(register=[0] * 4, rng=random.Random(1), mutate=0.0)
    pool = [60, 64, 67]
    first = [t.step(pool) for _ in range(4)]
    again = [t.step(pool) for _ in range(4)]
    assert first == again                       # mutate=0 -> perfect loop
    assert all(p in pool for p in first)


def test_turing_requantizes_to_new_pool() -> None:
    t = Turing(register=[60, 64, 67, 60], rng=random.Random(1), mutate=0.0)
    got = [t.step([61, 65, 68]) for _ in range(4)]
    assert all(p in (61, 65, 68) for p in got)  # chord changed -> snapped


def test_pitch_pool_registers_and_kinds() -> None:
    cfg = {"register": [72, 84], "pool": "chord"}
    pool = pitch_pool(cfg, [44, 51, 56, 60], [5, 7, 8, 10, 0, 1, 3])
    assert all(72 <= p <= 84 for p in pool)
    assert all(p % 12 in {8, 3, 0} for p in pool)
    cfg["pool"] = "scale"
    pool = pitch_pool(cfg, [44, 51, 56, 60], [5, 7, 8, 10, 0, 1, 3])
    assert {p % 12 for p in pool} <= {5, 7, 8, 10, 0, 1, 3}


def test_sim_seed_reproducible() -> None:
    if not SIM_BIN.exists():
        from unittest import SkipTest
        raise SkipTest("utrp-sim binary not built")
    import os
    env = dict(os.environ, UTRP_SIM_SEED="42")
    runs = [subprocess.run([str(SIM_BIN), "--measures", "10", "--key", "F",
                            "--mode", "aeolian"], capture_output=True,
                           text=True, check=True, env=env).stdout
            for _ in range(2)]
    assert runs[0] == runs[1]                   # same seed -> identical
    env["UTRP_SIM_SEED"] = "7"
    other = subprocess.run([str(SIM_BIN), "--measures", "10", "--key", "F",
                            "--mode", "aeolian"], capture_output=True,
                           text=True, check=True, env=env).stdout
    assert other != runs[0]                     # different seed -> differs


def test_sim_binary_contract() -> None:
    if not SIM_BIN.exists():
        from unittest import SkipTest
        raise SkipTest("utrp-sim binary not built")
    out = subprocess.run(
        [str(SIM_BIN), "--measures", "30", "--key", "F", "--mode", "aeolian"],
        capture_output=True, text=True, check=True)
    measures = json.loads(out.stdout)
    assert len(measures) == 30
    for m in measures:
        assert m["chords"] and m["chords"][-1]["role"] == "target"
        assert len(m["scale"]) == 7
        for c in m["chords"]:
            notes = c["notes"]
            assert all(24 <= n <= 96 for n in notes), notes
            assert all(b > a for a, b in zip(notes, notes[1:])), notes  # ascending
    # threshold semantics: first measures stay in the starting key
    assert measures[0]["key"].startswith("F"), measures[0]["key"]



def test_chord_ninth_uses_root_not_inverted_bass() -> None:
    cfg = {"register": [48, 84], "pool": "chord+9"}
    pcs = {n % 12 for n in pitch_pool(cfg, [52, 55, 59, 60], [0, 2, 4, 5, 7, 9, 11], 0)}
    assert 2 in pcs and 6 not in pcs


def test_octave_leap_keeps_pitch_class() -> None:
    from perform import octave_up_in_register
    for note in range(24, 97):
        for upper in range(note, 108):
            shifted = octave_up_in_register(note, upper)
            assert shifted <= upper and shifted % 12 == note % 12


if __name__ == "__main__":
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
    print("perform ok")
