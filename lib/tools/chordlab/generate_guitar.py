"""Compile complete hand-region pitch unions offline, without finger-count constraints."""
from dataclasses import dataclass
from pathlib import Path
import tomllib

STEPS = (0, 2, 4, 5, 7, 9, 11)


@dataclass(frozen=True)
class AnchorFamily:
    degrees: tuple[int, ...]
    reference_root: int
    anchors: tuple[int, ...]

    @classmethod
    def read(cls, data: object) -> "AnchorFamily":
        if not isinstance(data, dict):
            raise ValueError("Expected seventh anchor family table")
        degrees, root, anchors = data.get("degrees"), data.get("reference_root"), data.get("anchors")
        if (not isinstance(degrees, list) or not degrees or
                any(type(d) is not int or not 0 <= d < 7 for d in degrees) or
                len(set(degrees)) != len(degrees) or
                type(root) is not int or not 0 <= root < 12 or
                not isinstance(anchors, list) or not anchors or
                any(type(a) is not int or not 0 <= a <= 17 for a in anchors) or
                anchors != sorted(set(anchors))):
            raise ValueError("Invalid seventh anchor family")
        return cls(tuple(degrees), root, tuple(anchors))

    def positions(self, root: int, maximum: int) -> tuple[int, ...]:
        shift = (root - self.reference_root) % 12
        residues = frozenset((a + shift) % 12 for a in self.anchors)
        fretted = tuple(a for a in range(1, maximum + 1) if a % 12 in residues)
        # Open strings do not transpose like a fretted grip. Only explicit reference
        # open positions are enabled; Dm7/Bm7b5 do not acquire an unrequested fret 0.
        return ((0,) if shift == 0 and 0 in self.anchors else ()) + fretted


@dataclass(frozen=True)
class Rules:
    open_notes: tuple[int, ...]
    max_fret: int
    fret_span: int
    min_anchor: int
    max_anchor: int
    preferred_anchor: int
    min_anchor_gap: int
    seventh: tuple[AnchorFamily, ...]

    @classmethod
    def read(cls, path: Path) -> "Rules":
        data = tomllib.loads(path.read_text())
        names = ("max_fret", "fret_span", "min_anchor", "max_anchor",
                 "preferred_anchor", "min_anchor_gap")
        notes = data["open_notes"]
        if not isinstance(notes, list) or len(notes) != 6 or any(type(n) is not int for n in notes):
            raise ValueError("Expected six integer open-string MIDI notes")
        if any(type(data[n]) is not int for n in names):
            raise ValueError("Guitar limits must be integers")
        families = data.get("seventh")
        if not isinstance(families, dict) or len(families) != 4:
            raise ValueError("Expected four seventh anchor families")
        seventh = tuple(AnchorFamily.read(f) for f in families.values())
        if sorted(d for family in seventh for d in family.degrees) != list(range(7)):
            raise ValueError("Seventh families must cover each degree exactly once")
        rules = cls(tuple(notes), *(data[n] for n in names), seventh)
        if (rules.open_notes != (40, 45, 50, 55, 59, 64) or
                not 1 <= rules.min_anchor <= rules.preferred_anchor <= rules.max_anchor or
                not 0 < rules.fret_span <= 3 or
                rules.max_anchor + rules.fret_span > rules.max_fret or
                rules.max_fret > 20 or rules.min_anchor_gap != 2):
            raise ValueError("Unsupported guitar layout or fingering limits")
        return rules


@dataclass(frozen=True)
class Region:
    anchor: int
    pitches: tuple[int, ...]
    coverage: int  # String/fret locations, including same-pitch duplicates.



def chord_pcs(key: int, degree: int, kind: int) -> frozenset[int]:
    if not 0 <= key < 12 or not 0 <= degree < 7 or not 0 <= kind < 3:
        raise ValueError("Invalid chord")
    return frozenset((key + STEPS[(degree + 2 * i) % 7]) % 12 for i in range(3 + kind))


def region(rules: Rules, pcs: frozenset[int], anchor: int) -> Region:
    if not 0 <= anchor <= rules.max_anchor:
        raise ValueError("Anchor outside visible hand-region range")
    locations = tuple(o + f for o in rules.open_notes
                      for f in range(anchor, min(anchor + rules.fret_span, rules.max_fret) + 1)
                      if (o + f) % 12 in pcs)
    pitches = tuple(sorted(set(locations)))
    if frozenset(n % 12 for n in pitches) != pcs:
        raise ValueError(f"Incomplete chord in hand region: {anchor=}")
    return Region(anchor, pitches, len(locations))


def spaced_regions(regions: tuple[Region, ...], gap: int) -> tuple[Region, ...]:
    # Prefer more chord-tone locations, then lower anchor on ties. Reject only
    # direct neighbours; do not collapse an entire chain of adjacent positions.
    chosen: list[Region] = []
    for candidate in sorted(regions, key=lambda r: (-r.coverage, r.anchor)):
        if all(abs(candidate.anchor - other.anchor) >= gap for other in chosen):
            chosen.append(candidate)
    return tuple(sorted(chosen, key=lambda r: r.anchor))


def catalog(rules: Rules, key: int, degree: int, kind: int) -> tuple[Region, ...]:
    pcs = chord_pcs(key, degree, kind)
    root = (key + STEPS[degree]) % 12
    anchors = tuple(range(rules.min_anchor, rules.max_anchor + 1))
    if kind == 1:
        family = next(f for f in rules.seventh if degree in f.degrees)
        anchors = family.positions(root, rules.max_anchor)
    return spaced_regions(tuple(region(rules, pcs, a) for a in anchors), rules.min_anchor_gap)


def make_guitar(source: Path) -> str:
    rules = Rules.read(source / "guitar.toml")
    lines = ["// Generated by generate_guitar.py; do not edit. Anchor, count, sorted MIDI pitches.", "@init"]
    capacity = len(rules.open_notes) * (rules.fret_span + 1)
    stride = capacity + 2
    pointer = 10000
    for key in range(12):
        lines.append(f"function guitar_table_{key}() (")
        for degree in range(7):
            for kind in range(3):
                regions = catalog(rules, key, degree, kind)
                index = 6000 + (key * 21 + degree * 3 + kind) * 2
                lines.append(f"  {index}[0]={pointer}; {index}[1]={len(regions)};")
                for item in regions:
                    values = (item.anchor, len(item.pitches), *item.pitches,
                              *((-1,) * (capacity - len(item.pitches))))
                    lines.append("  " + " ".join(f"{pointer}[{i}]={v};" for i, v in enumerate(values)))
                    pointer += stride
        lines.append(");")
    lines.extend(f"guitar_table_{key}();" for key in range(12))
    lines.append(f"guitar_record_stride={stride};")
    lines.append(f"guitar_voice_capacity={capacity};")
    lines.append(f"guitar_default_anchor={rules.preferred_anchor};")
    lines.append(f"guitar_fret_span={rules.fret_span};")
    lines.append(f"guitar_max_fret={rules.max_fret};")
    lines.append(f"guitar_max_anchor={rules.max_anchor};")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    source = Path(__file__).resolve().parent
    (source / "guitar_table.jsfx-inc").write_text(make_guitar(source))
