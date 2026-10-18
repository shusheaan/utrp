from pathlib import Path

import numpy as np

from benchmark import Fixture, audio, evaluate, evaluate_overlap, overlapping, trace


def fixture() -> Fixture:
    return Fixture((40, 47, 52), 'harmonic', .3, 48000, 100, 400, 300, 20)


def test_signal_and_overlap() -> None:
    f = fixture()
    samples = audio(f)
    assert len(samples) == 38400
    assert np.all(samples[:4800] == 0)
    assert np.all(samples[24000:] == 0)
    assert np.max(np.abs(samples)) <= .30000001
    combined = overlapping(f, (0, 80, 160))
    assert len(combined) == 46080
    assert np.max(np.abs(combined)) <= .30000001


def test_latency_requires_whole_correct_set() -> None:
    result = evaluate(fixture(), ((0., ()), (110., (40,)), (130., (40, 47, 52)), (500., ())))
    assert result['first_exact_stable_ms'] == 30
    assert result['steady_exact_fraction'] == 1
    assert result['spurious_notes'] == []


def test_brief_or_extra_note_is_not_success() -> None:
    result = evaluate(fixture(), ((0., ()), (110., (40, 47, 52)), (119., (40, 47, 52, 64))))
    assert result['first_exact_stable_ms'] is None
    assert result['spurious_notes'] == [64]


def test_overlap_expected_set_changes_with_time() -> None:
    events = ((0., ()), (100., (40,)), (180., (40, 47)), (260., (40, 47, 52)),
              (500., (47, 52)), (580., (52,)), (660., ()))
    result = evaluate_overlap(fixture(), (0, 80, 160), events)
    assert result['exact_time_fraction_including_transitions'] == 1
    assert result['spurious_notes'] == []
