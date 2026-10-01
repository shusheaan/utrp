"""Phrase boundaries must be rejected before entering the native renderer."""
from __future__ import annotations

from pathlib import Path
import sys
from typing import cast

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from albumspec import PhraseNote, _phrase, load, validate_phrase


@pytest.mark.parametrize('period', [0.0, -1.0, float('nan'), float('inf')])
def test_invalid_pulse_period_is_rejected(period: float) -> None:
    with pytest.raises(ValueError, match='period'):
        _phrase({'dur': 1.0, 'pulses': {'t0': 0.0, 'until': 0.5,
                'period': period, 'gate': 0.1, 'notes': [60]}})


@pytest.mark.parametrize('note', [
    PhraseNote(-0.1, 60, 90, 0.2), PhraseNote(0.1, 60, 90, 2.0),
    PhraseNote(0.1, 60, 90, 0.0), PhraseNote(float('nan'), 60, 90, 0.2),
    PhraseNote(0.1, 128, 90, 0.2), PhraseNote(0.1, 60, 128, 0.2),
])
def test_invalid_note_is_rejected(note: PhraseNote) -> None:
    with pytest.raises(ValueError):
        validate_phrase((note,), 1.0)


@pytest.mark.parametrize('duration', [0.0, -1.0, float('nan'), float('inf')])
def test_invalid_phrase_duration_is_rejected(duration: float) -> None:
    with pytest.raises(ValueError):
        validate_phrase((PhraseNote(0.0, 60, 90, 0.1),), duration)


def test_existing_specs_and_exact_end_remain_valid() -> None:
    validate_phrase((PhraseNote(0.0, 60, 90, 1.0),), 1.0)
    paths = sorted((Path(__file__).parent / 'specs').glob('*.toml'))
    assert len(paths) == 4
    for path in paths:
        assert load(path).targets


def test_renderer_rejects_overrun_before_native_access() -> None:
    import surgepy
    from synth import render_phrase
    # This object has no native methods: validation must fail before accessing any.
    untouched = cast(surgepy.SurgeSynthesizer, object())
    with pytest.raises(ValueError, match='within phrase'):
        render_phrase(untouched, (PhraseNote(0.2, 60, 90, 2.0),), 1.0)
