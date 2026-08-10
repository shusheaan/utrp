"""Invariant checks for theory.py; runs under pytest or plain python."""
from __future__ import annotations

from theory import (MODES, QUALITIES, altered_degree, apply_voicing,
                    diatonic_seventh, secondary_dominant)


def test_c_major_diatonic() -> None:
    got = [(diatonic_seventh(0, "ionian", d).symbol()) for d in range(1, 8)]
    assert got == ["Cmaj7", "Dm7", "Em7", "Fmaj7", "G7", "Am7", "Bm7b5"], got


def test_a_aeolian_and_harmonic() -> None:
    assert diatonic_seventh(9, "aeolian", 1).symbol() == "Am7"
    assert diatonic_seventh(9, "harmonic-minor", 1).symbol() == "AmMaj7"
    assert diatonic_seventh(9, "harmonic-minor", 5).symbol() == "E7"
    assert diatonic_seventh(9, "harmonic-minor", 7).symbol() == "G#dim7"


def test_secondary_dominant() -> None:
    v_of_ii = secondary_dominant(0, "ionian", 2)
    assert v_of_ii.symbol() == "A7" and v_of_ii.degree_label == "V7/II"


def test_altered_degree() -> None:
    assert altered_degree(0, "b", 6, "maj7").symbol() == "G#maj7"   # Ab
    assert altered_degree(0, "b", 7, "7").symbol() == "A#7"         # Bb7


def test_voicing_shapes() -> None:
    close = ((1, 0), (3, 0), (5, 0), (7, 0))
    c = diatonic_seventh(0, "ionian", 1)
    assert apply_voicing(c, close, 48) == (48, 52, 55, 59)
    drop2 = ((5, -1), (1, 0), (3, 0), (7, 0))
    assert apply_voicing(c, drop2, 48) == (43, 48, 52, 59)
    d = diatonic_seventh(0, "ionian", 2)                            # Dm7
    assert apply_voicing(d, close, 48) == (50, 53, 57, 60)


def test_every_mode_every_degree_has_quality() -> None:
    for mode in MODES:
        for deg in range(1, 8):
            ch = diatonic_seventh(0, mode, deg)
            assert ch.quality in QUALITIES, (mode, deg, ch)


if __name__ == "__main__":
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
    print("theory ok")
