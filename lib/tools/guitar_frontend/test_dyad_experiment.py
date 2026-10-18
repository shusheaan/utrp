from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from dyad_experiment import Analysis, analyze_audio, classify
from dyad_study import Study, fretboard_pairs, synthesize


@pytest.fixture
def config() -> Analysis:
    return Analysis.from_file(Path(__file__).with_name('dyad_experiment.toml'))


@pytest.mark.parametrize('notes', [(50, 55), (57, 62), (76, 79)])
@pytest.mark.parametrize('frame_ms', [48, 64])
def test_resolved_pairs(config: Analysis, notes: tuple[int, int], frame_ms: int) -> None:
    settings = replace(config, frame_ms=frame_ms)
    signal = synthesize(notes, settings.frame_samples + settings.hop_samples,
                        settings.sample_rate, 'plucked', 42)
    frames = analyze_audio(signal, settings)
    assert frames[0].notes == ()  # no one-frame optimistic output
    assert frames[-1].notes == notes


@pytest.mark.parametrize('shape', ['sine', 'plucked', 'dominant', 'missing'])
@pytest.mark.parametrize('note', [40, 50, 57, 64, 76, 88])
def test_single_harmonic_series_is_not_two_notes(config: Analysis, shape: str, note: int) -> None:
    signal = synthesize((note,), config.frame_samples + config.hop_samples,
                        config.sample_rate, shape, 42)
    assert not any(f.notes for f in analyze_audio(signal, config))


@pytest.mark.parametrize('notes', [(40, 41), (52, 64), (52, 59)])
def test_ambiguous_pairs_abstain(config: Analysis, notes: tuple[int, int]) -> None:
    signal = synthesize(notes, config.frame_samples + config.hop_samples,
                        config.sample_rate, 'plucked', 42)
    assert not any(f.notes for f in analyze_audio(signal, config))


@pytest.mark.parametrize('value', [0.0, 0.1, 1.0, float('nan'), float('inf')])
def test_invalid_or_nonmusical_input(config: Analysis, value: float) -> None:
    assert classify(np.full(config.frame_samples, value), config).notes == ()


def test_frame_boundary(config: Analysis) -> None:
    for frame in (np.zeros(config.frame_samples-1), np.zeros((config.frame_samples, 2))):
        with pytest.raises(ValueError):
            classify(frame, config)
    with pytest.raises(ValueError):
        analyze_audio(np.zeros((100, 2)), config)
    assert analyze_audio(np.zeros(config.frame_samples-1), config) == ()


def test_causal_prefix_and_silence_release(config: Analysis) -> None:
    tone = synthesize((50, 55), config.sample_rate // 5, config.sample_rate, 'plucked', 42)
    prefix = analyze_audio(tone, config)
    assert any(f.notes for f in prefix)
    audio = np.concatenate((tone, np.zeros(config.sample_rate // 5)))
    full = analyze_audio(audio, config)
    assert full[:len(prefix)] == prefix  # later samples cannot change earlier output
    assert not full[-1].notes


def test_all_fretboard_pairs_are_enumerated() -> None:
    study = Study.from_file(Path(__file__).with_name('dyad_experiment.toml'))
    pairs = fretboard_pairs(study)
    assert len(pairs) == 1156
    assert all(a < b for a, b in pairs)
    assert (40, 88) in pairs
    assert (87, 88) not in pairs  # both only available on string 1; not a playable dyad
    assert (50, 55) in pairs


@pytest.mark.parametrize('old,new', [('frame_ms = 64', 'frame_ms = 0'),
                                     ('hop_ms = 8', 'hop_ms = true'),
                                     ('peak_floor = 0.08', 'peak_floor = nan'),
                                     ('minimum_balance = 0.55', 'minimum_balance = 2.0')])
def test_invalid_config(tmp_path: Path, old: str, new: str) -> None:
    source = Path(__file__).with_name('dyad_experiment.toml').read_text()
    path = tmp_path / 'invalid.toml'
    path.write_text(source.replace(old, new))
    with pytest.raises(ValueError):
        Analysis.from_file(path)


@pytest.mark.parametrize('frame_ms', [48, 64])
@pytest.mark.parametrize('notes', [(41, 46), (47, 48), (54, 62), (60, 61)])
def test_two_peaks_alone_are_not_independent_strings(config: Analysis, frame_ms: int,
                                                    notes: tuple[int, int]) -> None:
    settings = replace(config, frame_ms=frame_ms)
    signal = synthesize(notes, settings.sample_rate // 5, settings.sample_rate, 'sine', 42)
    padded = np.concatenate((np.zeros(settings.sample_rate // 10), signal,
                             np.zeros(settings.sample_rate // 10)))
    assert not any(f.notes for f in analyze_audio(padded, settings))


def test_very_unequal_pair_is_outside_experiment(config: Analysis) -> None:
    signal = synthesize((50, 55), config.sample_rate // 5, config.sample_rate,
                        'plucked', 42, balance=0.1)
    assert not any(f.notes for f in analyze_audio(signal, config))
