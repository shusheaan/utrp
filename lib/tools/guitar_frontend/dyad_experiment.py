"""Conservative, offline two-pitch hypothesis test; not a real-time plugin.

Each accepted fundamental must have an independently resolved peak. A single
harmonic series is preferred to a two-note explanation, including missing-root
ambiguities. Silence means abstention, never proof of accurate recognition.
"""
from dataclasses import dataclass
from itertools import combinations
from math import isfinite
from pathlib import Path
import tomllib

import numpy as np
from numpy.typing import NDArray
from scipy.signal import find_peaks


@dataclass(frozen=True)
class Analysis:
    sample_rate: int
    frame_ms: int
    hop_ms: int
    stable_frames: int
    gate_db: float
    min_note: int
    max_note: int
    max_harmonic: int
    minimum_independent_partials: int
    peak_floor: float
    cents_tolerance: float
    minimum_balance: float
    minimum_coverage: float
    ambiguity_margin: float
    minimum_separation_bins: float

    @classmethod
    def from_file(cls, path: Path) -> 'Analysis':
        data = tomllib.loads(path.read_text())['analysis']
        integer = ('sample_rate', 'frame_ms', 'hop_ms', 'stable_frames',
                   'min_note', 'max_note', 'max_harmonic', 'minimum_independent_partials')
        floating = ('gate_db', 'peak_floor', 'cents_tolerance', 'minimum_balance',
                    'minimum_coverage', 'ambiguity_margin', 'minimum_separation_bins')
        if set(data) != set(integer + floating):
            raise ValueError('Unexpected analysis settings')
        for key in integer:
            if type(data[key]) is not int:
                raise ValueError(f'Expected integer: {key}')
        for key in floating:
            if type(data[key]) not in (int, float) or not isfinite(data[key]):
                raise ValueError(f'Expected finite number: {key}')
        result = cls(**data)
        if not (32000 <= result.sample_rate <= 192000 and 32 <= result.frame_ms <= 128
                and 1 <= result.hop_ms < result.frame_ms and 1 <= result.stable_frames <= 8
                and 24 <= result.min_note < result.max_note <= 108
                and 2 <= result.max_harmonic <= 24 and 2 <= result.minimum_independent_partials <= 4 and -80 <= result.gate_db <= -12
                and 0 < result.peak_floor < 1 and 0 < result.cents_tolerance < 50
                and 0 < result.minimum_balance <= 1 and 0.5 < result.minimum_coverage <= 1
                and 0 <= result.ambiguity_margin < 1 and 1 <= result.minimum_separation_bins <= 4):
            raise ValueError('Analysis setting outside supported bounds')
        return result

    @property
    def frame_samples(self) -> int:
        return round(self.sample_rate * self.frame_ms / 1000)

    @property
    def hop_samples(self) -> int:
        return round(self.sample_rate * self.hop_ms / 1000)


@dataclass(frozen=True)
class Peak:
    hz: float
    power: float


@dataclass(frozen=True)
class Decision:
    notes: tuple[int, ...]
    reason: str
    coverage: float = 0.0


def frequency(note: int) -> float:
    return 440.0 * 2.0 ** ((note - 69) / 12.0)


def spectral_peaks(frame: NDArray[np.float64], config: Analysis) -> tuple[Peak, ...]:
    centered = frame - np.mean(frame)
    nfft = 1 << (len(frame) * 8 - 1).bit_length()
    magnitude = np.abs(np.fft.rfft(centered * np.hanning(len(frame)), n=nfft))
    maximum = float(np.max(magnitude))
    if maximum <= 0:
        return ()
    bins, _ = find_peaks(magnitude, height=maximum * config.peak_floor)
    peaks: list[Peak] = []
    for index in bins:
        if index == 0 or index + 1 >= len(magnitude):
            continue
        left, center, right = np.log(np.maximum(magnitude[index-1:index+2], 1e-30))
        denominator = left - 2 * center + right
        shift = float(0.5 * (left - right) / denominator) if abs(denominator) > 1e-20 else 0.0
        hz = (int(index) + shift) * config.sample_rate / nfft
        if hz >= frequency(config.min_note) * 0.8:
            peaks.append(Peak(hz, float(magnitude[index] ** 2)))
    return tuple(peaks)


def harmonic_match(hz: float, root: float, config: Analysis) -> bool:
    harmonic = round(hz / root)
    return (1 <= harmonic <= config.max_harmonic
            and abs(1200 * np.log2(hz / (harmonic * root))) <= config.cents_tolerance)


def candidate_peaks(peaks: tuple[Peak, ...], config: Analysis) -> tuple[tuple[int, Peak], ...]:
    candidates: dict[int, Peak] = {}
    for peak in peaks:
        midi = 69 + 12 * np.log2(peak.hz / 440)
        note = round(float(midi))
        if config.min_note <= note <= config.max_note and abs(midi - note) * 100 <= config.cents_tolerance:
            if note not in candidates or peak.power > candidates[note].power:
                candidates[note] = peak
    return tuple(sorted(candidates.items()))


def fundamental_candidates(peaks: tuple[Peak, ...], config: Analysis) -> tuple[tuple[int, Peak], ...]:
    """Do not rescue an ambiguous lower root by calling its overtone a new note.

    The lower peak may itself belong to another string's harmonic series. That
    is ambiguity, not evidence to promote the upper peak by an octave. Reject
    conservatively rather than fitting the same spectrum with invented notes.
    """
    return tuple((note, peak) for note, peak in candidate_peaks(peaks, config)
                 if not any(round(peak.hz / lower.hz) >= 2
                            and harmonic_match(peak.hz, lower.hz, config)
                            for lower in peaks))


def lower_root_evidence(hz: float, other_hz: float, peaks: tuple[Peak, ...],
                        config: Analysis) -> bool:
    """Reject an octave guess if independent odd partials support a lower root.

    A missing/merged fundamental need not appear as a peak. The accepted root
    already supplies one partial; another peak outside both chosen harmonic
    series supplies additional evidence. Coverage alone can hide this weaker
    peak below its allowed residual error.
    """
    for divisor in range(2, config.max_harmonic+1):
        lower = hz/divisor
        if lower < frequency(config.min_note):
            break
        if any(harmonic_match(p.hz, lower, config)
               and not harmonic_match(p.hz, hz, config)
               and not harmonic_match(p.hz, other_hz, config) for p in peaks):
            return True
    return False


def classify(frame: NDArray[np.float64], config: Analysis) -> Decision:
    if frame.ndim != 1 or len(frame) != config.frame_samples:
        raise ValueError('Expected one complete mono analysis frame')
    if not np.all(np.isfinite(frame)):
        return Decision((), 'nonfinite')
    if np.max(np.abs(frame)) >= 1:
        return Decision((), 'clipped')
    centered = frame - np.mean(frame)
    if float(np.sqrt(np.mean(centered * centered))) < 10 ** (config.gate_db / 20):
        return Decision((), 'below_gate')
    peaks = spectral_peaks(frame, config)
    total = sum(p.power for p in peaks)
    if not peaks or total <= 0:
        return Decision((), 'no_peaks')
    # A missing/weak fundamental is NOT evidence of a second string.
    for root in range(config.min_note, config.max_note + 1):
        covered = sum(p.power for p in peaks if harmonic_match(p.hz, frequency(root), config)) / total
        if covered >= config.minimum_coverage:
            return Decision((), 'single_series_ambiguous', covered)
    choices: list[tuple[float, tuple[int, int]]] = []
    for (low, a), (high, b) in combinations(fundamental_candidates(peaks, config), 2):
        if b.hz - a.hz < config.minimum_separation_bins * 1000 / config.frame_ms:
            continue
        if min(a.power, b.power) < max(a.power, b.power) * config.minimum_balance ** 2:
            continue
        if harmonic_match(b.hz, a.hz, config):
            continue
        independent_a = sum(harmonic_match(p.hz, a.hz, config) and not harmonic_match(p.hz, b.hz, config) for p in peaks)
        independent_b = sum(harmonic_match(p.hz, b.hz, config) and not harmonic_match(p.hz, a.hz, config) for p in peaks)
        if min(independent_a, independent_b) < config.minimum_independent_partials:
            continue
        if lower_root_evidence(a.hz, b.hz, peaks, config) or lower_root_evidence(b.hz, a.hz, peaks, config):
            continue
        coverage = sum(p.power for p in peaks if harmonic_match(p.hz, a.hz, config)
                       or harmonic_match(p.hz, b.hz, config)) / total
        if coverage >= config.minimum_coverage:
            choices.append((coverage, (low, high)))
    choices.sort(reverse=True)
    if not choices:
        return Decision((), 'unresolved')
    if len(choices) > 1 and choices[0][0] - choices[1][0] < config.ambiguity_margin:
        return Decision((), 'multiple_explanations', choices[0][0])
    return Decision(choices[0][1], 'accepted', choices[0][0])


@dataclass(frozen=True)
class TimedDecision:
    samples: int
    notes: tuple[int, ...]
    reason: str


def analyze_audio(audio: NDArray[np.float64], config: Analysis) -> tuple[TimedDecision, ...]:
    """Causal frames with immediate abstention; no future samples or release hold."""
    if audio.ndim != 1:
        raise ValueError('Expected mono audio')
    previous: tuple[int, ...] = ()
    stable = 0
    output: list[TimedDecision] = []
    for end in range(config.frame_samples, len(audio) + 1, config.hop_samples):
        decision = classify(audio[end-config.frame_samples:end], config)
        stable = stable + 1 if decision.notes and decision.notes == previous else 1
        previous = decision.notes
        notes = decision.notes if stable >= config.stable_frames else ()
        output.append(TimedDecision(end, notes, decision.reason))
    return tuple(output)
