"""Catalog invariants are independent of the renderer and host wrapper."""
from pathlib import Path
import importlib.util
import sys

import pytest

SOURCE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("chordlab_guitar", SOURCE / "generate_guitar.py")
assert SPEC is not None and SPEC.loader is not None
GUITAR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GUITAR
SPEC.loader.exec_module(GUITAR)


@pytest.mark.parametrize("key", range(12))
@pytest.mark.parametrize("degree", range(7))
@pytest.mark.parametrize("kind", range(3))
def test_complete_hand_regions(key: int, degree: int, kind: int) -> None:
    rules = GUITAR.Rules.read(SOURCE / "guitar.toml")
    regions = GUITAR.catalog(rules, key, degree, kind)
    assert regions
    anchors = tuple(r.anchor for r in regions)
    assert all(b - a >= 2 for a, b in zip(anchors, anchors[1:]))
    pcs = frozenset((key + (0, 2, 4, 5, 7, 9, 11)[(degree + 2*i) % 7]) % 12
                    for i in range(3 + kind))
    for item in regions:
        locations = tuple(o + f for o in (40, 45, 50, 55, 59, 64)
                          for f in range(item.anchor, item.anchor + 3) if (o+f) % 12 in pcs)
        assert item.pitches == tuple(sorted(set(locations)))
        assert item.coverage == len(locations)
        assert frozenset(n % 12 for n in item.pitches) == pcs
        assert all(38 <= n <= 86 for n in item.pitches)
        assert len(item.pitches) <= 18


def test_generated_catalog_is_current() -> None:
    assert (SOURCE / "guitar_table.jsfx-inc").read_text() == GUITAR.make_guitar(SOURCE)


def test_no_clef_mode_controls_but_anchor_markers_remain() -> None:
    ui = (SOURCE / "ui.jsfx-inc").read_text()
    engine = (SOURCE / "chordlab.jsfx").read_text()
    for removed in ("draw_voicing_modes", "Piano [J]", "Guitar [K]", "Fret %d"):
        assert removed not in ui + engine
    assert "guitar_anchor_state(fret)" in ui
    assert "gfx_circle(kx,y-6,marker_radius,anchor_state==2,1)" in ui


def test_region_is_shared_by_all_diagrams_and_midi() -> None:
    ui = (SOURCE / "ui.jsfx-inc").read_text()
    staff = (SOURCE / "staff.jsfx-inc").read_text()
    midi = (SOURCE / "midi.jsfx-inc").read_text()
    assert "guitar_region_contains" not in ui
    assert "candidate" not in ui
    assert "lit=(sounding && own[note]) || hw>0" in ui
    assert "note_dot(x,y-.5,role,note,scale_view,note_radius)" in staff
    assert "loop(voicing_mode ? region[1] : voice_count," in midi
    assert "n=voicing_mode ? region[i+2]" in midi
    assert "shape[6-string]" not in ui
    assert "guitar_fret_span=2;" in GUITAR.make_guitar(SOURCE)


@pytest.mark.parametrize("values", [(-1, 0, 0), (12, 0, 0), (0, 7, 0), (0, 0, 3)])
def test_invalid_chord_rejected(values: tuple[int, int, int]) -> None:
    with pytest.raises(ValueError):
        GUITAR.chord_pcs(*values)


@pytest.mark.parametrize("degree,expected", [
    (0, (0, 3, 5, 8, 10, 12)),
    (1, (2, 5, 7, 10, 12, 14)),
    (4, (0, 3, 5, 7, 10, 12)),
    (6, (3, 6, 10, 12, 14)),
])
def test_user_reference_seventh_anchors(degree: int, expected: tuple[int, ...]) -> None:
    rules = GUITAR.Rules.read(SOURCE / "guitar.toml")
    assert tuple(s.anchor for s in GUITAR.catalog(rules, 0, degree, 1)) == expected


@pytest.mark.parametrize("key", range(12))
@pytest.mark.parametrize("degree", range(7))
def test_seventh_anchors_only_use_transposed_user_candidates(key: int, degree: int) -> None:
    rules = GUITAR.Rules.read(SOURCE / "guitar.toml")
    reference_root, anchors = (
        (0, (0, 3, 5, 8, 10, 12)) if degree in (0, 3) else
        (2, (2, 5, 7, 10, 12, 14)) if degree in (1, 2, 5) else
        (7, (0, 3, 5, 7, 10, 12)) if degree == 4 else
        (11, (2, 3, 6, 7, 9, 10, 12)))
    root = (key + (0, 2, 4, 5, 7, 9, 11)[degree]) % 12
    candidates = tuple(a for a in range(15) if (
        (a > 0 and any((a-base-root+reference_root) % 12 == 0 for base in anchors)) or
        (a == 0 and 0 in anchors and root == reference_root)))
    family = next(f for f in rules.seventh if degree in f.degrees)
    assert family.positions(root, 14) == candidates
    selected = GUITAR.catalog(rules, key, degree, 1)
    pcs = GUITAR.chord_pcs(key, degree, 1)
    assert {r.anchor for r in selected} <= set(candidates)
    for omitted in set(candidates) - {r.anchor for r in selected}:
        coverage = GUITAR.region(rules, pcs, omitted).coverage
        assert any(abs(r.anchor - omitted) == 1 and
                   (r.coverage > coverage or (r.coverage == coverage and r.anchor < omitted))
                   for r in selected)


def test_spacing_keeps_higher_coverage_then_lower_anchor() -> None:
    regions = tuple(GUITAR.Region(a, (60,), c) for a, c in ((2, 4), (3, 5), (6, 7), (7, 7), (9, 9)))
    assert tuple(r.anchor for r in GUITAR.spaced_regions(regions, 2)) == (3, 6, 9)


@pytest.mark.parametrize("value", [
    None, {}, {"degrees": [0], "reference_root": 0, "anchors": []},
    {"degrees": [0, 0], "reference_root": 0, "anchors": [0, 3]},
    {"degrees": [7], "reference_root": 0, "anchors": [0, 3]},
    {"degrees": [0], "reference_root": True, "anchors": [0, 3]},
    {"degrees": [0], "reference_root": 12, "anchors": [0, 3]},
    {"degrees": [0], "reference_root": 0, "anchors": [3, 2]},
    {"degrees": [0], "reference_root": 0, "anchors": [-1, 3]},
    {"degrees": [0], "reference_root": 0, "anchors": [0, 18]},
    {"degrees": [0], "reference_root": 0, "anchors": [False, 3]},
])
def test_invalid_anchor_family_rejected(value: object) -> None:
    with pytest.raises(ValueError):
        GUITAR.AnchorFamily.read(value)


def test_seventh_degree_partition_validated(tmp_path: Path) -> None:
    path = tmp_path / "guitar.toml"
    path.write_text((SOURCE / "guitar.toml").read_text().replace("degrees = [0, 3]", "degrees = [0, 2]"))
    with pytest.raises(ValueError, match="each degree exactly once"):
        GUITAR.Rules.read(path)


@pytest.mark.parametrize("anchor", [-1, 15])
def test_invalid_region_anchor_rejected(anchor: int) -> None:
    rules = GUITAR.Rules.read(SOURCE / "guitar.toml")
    with pytest.raises(ValueError, match="Anchor"):
        GUITAR.region(rules, frozenset((0, 4, 7)), anchor)


def test_region_does_not_silently_omit_invalid_pitch_class() -> None:
    rules = GUITAR.Rules.read(SOURCE / "guitar.toml")
    with pytest.raises(ValueError, match="Incomplete"):
        GUITAR.region(rules, frozenset((0, 12)), 0)
