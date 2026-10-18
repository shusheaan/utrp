from pathlib import Path

import numpy as np
import pytest

from dyad_experiment import Analysis, Peak, analyze_audio, fundamental_candidates
from dyad_safety_study import melody_audio, melody_screen, single_attacks
from dyad_study import Study, fretboard_pairs, synthesize


@pytest.fixture
def config_path() -> Path:
    return Path(__file__).with_name('dyad_speed.toml')


def test_complete_single_note_attacks_and_releases(config_path: Path) -> None:
    rows = single_attacks(Analysis.from_file(config_path), Study.from_file(config_path))
    assert len(rows) == 196
    assert not any(row['false_pair_frames'] for row in rows)


def test_nonoverlapping_melodies_never_become_pairs(config_path: Path) -> None:
    rows = melody_screen(Analysis.from_file(config_path), Study.from_file(config_path))
    assert len(rows) == 40
    assert not any(row['false_pair_frames'] for row in rows)


@pytest.mark.parametrize('note', [52, 54])
def test_strong_mono_attack_cannot_become_two_pitches(config_path: Path,
                                                   note: int) -> None:
    config, study = Analysis.from_file(config_path), Study.from_file(config_path)
    signal = synthesize((note,), round(config.sample_rate*study.hold_ms/1000),
                        config.sample_rate, 'dominant', study.seed+note)
    pad = np.zeros(round(config.sample_rate*study.silence_ms/1000))
    audio = np.concatenate((pad, signal, pad))
    # These complete attacks/releases broke the rejected two-frame candidate.
    # Validate the actual three-frame configuration, not only its steady tone.
    assert not any(frame.notes for frame in analyze_audio(audio, config))


def test_weaker_resolved_pair_still_requires_repeated_evidence(config_path: Path) -> None:
    config = Analysis.from_file(config_path)
    signal = synthesize((50, 55), config.sample_rate//5, config.sample_rate,
                        'plucked', 42, balance=0.3)
    frames = analyze_audio(signal, config)
    assert all(not frame.notes for frame in frames[:config.stable_frames-1])
    assert any(frame.notes == (50, 55) for frame in frames)
    assert all(not frame.notes or frame.notes == (50, 55) for frame in frames)


def test_no_future_samples_or_hold_to_conceal_abstention(config_path: Path) -> None:
    config, study = Analysis.from_file(config_path), Study.from_file(config_path)
    signal = melody_audio((50, 55, 50), config, study, 'plucked', 0)
    prefix = analyze_audio(signal[:config.sample_rate//4], config)
    assert analyze_audio(signal, config)[:len(prefix)] == prefix
    pair = synthesize((50, 55), config.sample_rate//5, config.sample_rate, 'plucked', 42)
    frames = analyze_audio(np.concatenate((pair, np.zeros(config.sample_rate//5))), config)
    assert any(frame.notes for frame in frames)
    assert not frames[-1].notes


def test_candidate_cannot_promote_an_observed_root_to_its_octave(config_path: Path) -> None:
    config = Analysis.from_file(config_path)
    peaks = (Peak(82.4069, 1.0), Peak(587.3295, 0.7), Peak(1174.659, 0.3))
    # D5 is close to E2's seventh partial. That ambiguity must not turn into D6.
    assert [note for note, _ in fundamental_candidates(peaks, config)] == [40]


@pytest.mark.parametrize('notes', [(40, 74), (40, 76), (41, 75), (42, 76)])
def test_ambiguous_root_does_not_generate_upper_octave(config_path: Path,
                                                    notes: tuple[int, int]) -> None:
    config, study = Analysis.from_file(config_path), Study.from_file(config_path)
    index = fretboard_pairs(study).index(notes)
    signal = synthesize(notes, round(config.sample_rate*study.hold_ms/1000),
                        config.sample_rate, 'plucked', study.seed+index)
    pad = np.zeros(round(config.sample_rate*study.silence_ms/1000))
    frames = analyze_audio(np.concatenate((pad, signal, pad)), config)
    assert all(not frame.notes or frame.notes == notes for frame in frames)


@pytest.mark.parametrize('notes', [(52, 56), (58, 61), (64, 66), (72, 73), (75, 76)])
def test_unresolved_weak_fundamental_does_not_jump_octave(config_path: Path,
                                                       notes: tuple[int, int]) -> None:
    config, study = Analysis.from_file(config_path), Study.from_file(config_path)
    index = fretboard_pairs(study).index(notes)
    size = round(config.sample_rate*study.hold_ms/1000)
    signal = synthesize(notes, size, config.sample_rate, 'rich', study.seed+index+1,
                        cents=study.holdout_cents, balance=0.5)
    signal += np.random.default_rng(study.seed+index).normal(0, study.holdout_noise_rms, size)
    pad = np.zeros(round(config.sample_rate*study.silence_ms/1000))
    frames = analyze_audio(np.concatenate((pad, signal, pad)), config)
    assert all(not frame.notes or frame.notes == notes for frame in frames)
