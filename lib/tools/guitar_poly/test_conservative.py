from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from pytest import MonkeyPatch
from numpy.typing import NDArray

from benchmark import Fixture, audio, evaluate
import conservative
from conservative import Config, Decision, Peak, analyze, detect, harmonic_indices


def config() -> Config:
    return Config.load(Path(__file__).with_name('conservative.toml'))


@pytest.mark.parametrize('notes', [(50,), (55,), (50, 55), (50, 55, 59)])
@pytest.mark.parametrize('level', [.03, .1, .3])
def test_dg_harmonic_fixture(notes: tuple[int, ...], level: float) -> None:
    c = config()
    f = Fixture(notes, 'harmonic', level, c.sample_rate, 100, 400, 300, 20)
    result = evaluate(f, detect(audio(f), c))
    assert result['spurious_notes'] == []
    assert result['first_exact_stable_ms'] is not None
    assert result['steady_exact_fraction'] > .7
    assert result['held_at_end'] == ()


def test_noise_silence_dc_and_clipping_reject() -> None:
    c = config()
    size = c.sample_rate * c.frame_ms // 1000
    assert analyze(np.zeros(size), c) == Decision((), 'quiet')
    assert analyze(np.full(size, .1), c) == Decision((), 'quiet')
    assert analyze(np.random.default_rng(411).normal(0, .05, size), c).notes == ()
    assert analyze(np.full(size, 1.0), c) == Decision((), 'clipping')


def test_sine_without_independent_harmonics_abstains() -> None:
    c = config()
    f = Fixture((50, 55), 'sine', .3, c.sample_rate, 100, 400, 300, 20)
    assert all(not notes for _, notes in detect(audio(f), c))


def test_detuned_note_not_rounded_into_confident_pitch() -> None:
    c = config()
    t = np.arange(c.sample_rate * c.frame_ms // 1000) / c.sample_rate
    frequency = 146.8323839587 * 2 ** (40 / 1200)
    signal = sum(.1 * np.sin(2 * np.pi * frequency * h * t) / h ** 1.4 for h in range(1, 9))
    assert analyze(signal, c).notes == ()


def test_reject_clears_display_and_dense_input_latches(monkeypatch: MonkeyPatch) -> None:
    c = replace(config(), frame_ms=16, stable_frames=2, quiet_rearm_frames=2)
    decisions = iter([Decision((50, 55), 'candidate_not_certified')] * 2 +
                     [Decision((), 'unexplained_spectrum')] +
                     [Decision((50, 55), 'candidate_not_certified')] * 2 +
                     [Decision((), 'too_many_voices')] +
                     [Decision((50,), 'candidate_not_certified')] * 4 +
                     [Decision((), 'quiet')] * 2 +
                     [Decision((50,), 'candidate_not_certified')] * 2)

    def fake_analyze(frame: NDArray[np.float64], settings: Config) -> Decision:
        return next(decisions)

    monkeypatch.setattr(conservative, 'analyze', fake_analyze)
    samples = np.zeros(c.sample_rate * (16 + 13 * 8) // 1000)
    assert detect(samples, c) == ((0., ()), (24., (50, 55)), (32., ()),
                                 (48., (50, 55)), (56., ()), (120., (50,)))


def test_causal_prefix_has_identical_events() -> None:
    c = config()
    f = Fixture((50, 55), 'harmonic', .3, c.sample_rate, 100, 400, 300, 20)
    samples = audio(f)
    prefix = c.sample_rate * 300 // 1000
    full = tuple(e for e in detect(samples, c) if e[0] <= 300)
    assert full == detect(samples[:prefix], c)


@pytest.mark.parametrize('field,value', [('sample_rate', 0), ('sample_rate', True),
                                        ('stable_frames', 0), ('max_voices', 4),
                                        ('harmonics', 1), ('minimum_concentration', float('nan')),
                                        ('max_frequency', float('inf')), ('gate_db', 1),
                                        ('pitch_tolerance_cents', 60), ('fft_padding', 100)])
def test_invalid_config(field: str, value: float) -> None:
    with pytest.raises(ValueError):
        replace(config(), **{field: value})


@pytest.mark.parametrize('samples', [np.array([float('nan')]), np.zeros((2, 10)), np.ones(10)])
def test_invalid_frame(samples: NDArray[np.float64]) -> None:
    with pytest.raises(ValueError):
        analyze(samples, config())


def test_invalid_stream() -> None:
    with pytest.raises(ValueError):
        detect(np.array([float('inf')]), config())


def test_multiple_peaks_in_one_harmonic_are_not_independent() -> None:
    values = (Peak(150., 1.), Peak(299., .3), Peak(301., .2), Peak(450., .2))
    assert harmonic_indices(150., values, config()) == (0, 1, 3)


@pytest.mark.parametrize('rate', [32000, 44100, 96000, 192000])
def test_dg_at_supported_sample_rates(rate: int) -> None:
    c = replace(config(), sample_rate=rate)
    f = Fixture((50, 55), 'harmonic', .3, rate, 100, 400, 300, 20)
    result = evaluate(f, detect(audio(f), c))
    assert result['spurious_notes'] == []
    assert result['first_exact_stable_ms'] is not None
