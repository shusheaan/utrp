"""Pure chord/scale theory: modes, diatonic sevenths, voicing application.

No I/O, no state — mirrors the Rust utrp theory module (tone/key/chord) in
spirit: pick a key+mode, every scale degree yields a seventh chord, a voicing
pattern turns it into concrete MIDI notes.
"""
from __future__ import annotations

from dataclasses import dataclass

NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

MODES: dict[str, tuple[int, ...]] = {
    "ionian":         (0, 2, 4, 5, 7, 9, 11),
    "dorian":         (0, 2, 3, 5, 7, 9, 10),
    "phrygian":       (0, 1, 3, 5, 7, 8, 10),
    "lydian":         (0, 2, 4, 6, 7, 9, 11),
    "mixolydian":     (0, 2, 4, 5, 7, 9, 10),
    "aeolian":        (0, 2, 3, 5, 7, 8, 10),
    "locrian":        (0, 1, 3, 5, 6, 8, 10),
    "harmonic-minor": (0, 2, 3, 5, 7, 8, 11),
    "melodic-minor":  (0, 2, 3, 5, 7, 9, 11),
}

# chord-tone semitones per quality; tensions come from TENSIONS
QUALITIES: dict[str, dict[int, int]] = {
    "maj7":   {1: 0, 3: 4, 5: 7, 7: 11},
    "7":      {1: 0, 3: 4, 5: 7, 7: 10},
    "m7":     {1: 0, 3: 3, 5: 7, 7: 10},
    "m7b5":   {1: 0, 3: 3, 5: 6, 7: 10},
    "dim7":   {1: 0, 3: 3, 5: 6, 7: 9},
    "mMaj7":  {1: 0, 3: 3, 5: 7, 7: 11},
    "maj7#5": {1: 0, 3: 4, 5: 8, 7: 11},
    "7sus4":  {1: 0, 3: 5, 5: 7, 7: 10},
    "6":      {1: 0, 3: 4, 5: 7, 7: 9},
    "m6":     {1: 0, 3: 3, 5: 7, 7: 9},
}
TENSIONS = {9: 14, 11: 17, 13: 21}

_SEVENTH_NAME = {(4, 7, 11): "maj7", (3, 7, 10): "m7", (4, 7, 10): "7",
                 (3, 6, 10): "m7b5", (3, 6, 9): "dim7", (3, 7, 11): "mMaj7",
                 (4, 8, 11): "maj7#5"}


@dataclass(frozen=True)
class ChordSpec:
    root_pc: int              # pitch class 0-11
    quality: str              # key into QUALITIES
    degree_label: str         # e.g. "II", "V7/III", "bVI"

    def symbol(self) -> str:
        return f"{NOTE_NAMES[self.root_pc]}{self.quality}"


def diatonic_seventh(key_pc: int, mode: str, degree: int) -> ChordSpec:
    """degree is 1-based; quality read off the stacked scale thirds."""
    scale = MODES[mode]
    d = degree - 1
    root = scale[d]
    ivs = tuple(sorted((scale[(d + s) % 7] - root) % 12 for s in (2, 4, 6)))
    quality = _SEVENTH_NAME.get(ivs, "7")
    roman = ("I", "II", "III", "IV", "V", "VI", "VII")[d]
    return ChordSpec((key_pc + root) % 12, quality, roman)


def secondary_dominant(key_pc: int, mode: str, degree: int) -> ChordSpec:
    target = diatonic_seventh(key_pc, mode, degree)
    return ChordSpec((target.root_pc + 7) % 12, "7",
                     f"V7/{target.degree_label}")


def altered_degree(key_pc: int, accidental: str, degree: int,
                   quality: str) -> ChordSpec:
    root = (key_pc + MODES["ionian"][degree - 1]
            + {"b": -1, "#": 1}[accidental]) % 12
    roman = ("I", "II", "III", "IV", "V", "VI", "VII")[degree - 1]
    return ChordSpec(root, quality, f"{accidental}{roman}")


def apply_voicing(chord: ChordSpec, pattern: tuple[tuple[int, int], ...],
                  root_midi: int) -> tuple[int, ...]:
    """pattern = ((degree, octave), ...) bass-to-top; returns MIDI notes."""
    tones = QUALITIES[chord.quality]
    base = root_midi - root_midi % 12 + chord.root_pc
    if base < root_midi - 6:
        base += 12
    out = []
    for degree, octave in pattern:
        semi = tones.get(degree)
        if semi is None:
            semi = TENSIONS[degree]
        out.append(base + semi + 12 * octave)
    return tuple(out)


def note_name(midi: int) -> str:
    return f"{NOTE_NAMES[midi % 12]}{midi // 12 - 1}"
