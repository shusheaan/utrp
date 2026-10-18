"""Offline conservative harmonic sieve; never imported by the production CLAP."""
from dataclasses import dataclass
import math
from pathlib import Path
import tomllib

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class Config:
    sample_rate: int
    frame_ms: int
    hop_ms: int
    fft_padding: int
    min_note: int
    max_note: int
    max_frequency: float
    harmonics: int
    peak_floor_ratio: float
    fundamental_floor_ratio: float
    harmonic_tolerance_cents: float
    pitch_tolerance_cents: float
    minimum_harmonics: int
    minimum_coverage: float
    minimum_concentration: float
    gate_db: float
    clipping_level: float
    max_voices: int
    stable_frames: int
    quiet_rearm_frames: int

    @classmethod
    def load(cls, path: Path) -> 'Config':
        document = tomllib.loads(path.read_text())
        if set(document) != {'analysis'}:
            raise ValueError('Expected only [analysis]')
        return cls(**document['analysis'])

    def __post_init__(self) -> None:
        for field in ('sample_rate', 'frame_ms', 'hop_ms', 'fft_padding', 'min_note',
                      'max_note', 'harmonics', 'minimum_harmonics', 'max_voices',
                      'stable_frames', 'quiet_rearm_frames'):
            value = getattr(self, field)
            if type(value) is not int or value < 1:
                raise ValueError(f'{field} must be a positive integer')
        for field in ('peak_floor_ratio', 'fundamental_floor_ratio', 'minimum_coverage',
                      'minimum_concentration', 'clipping_level'):
            value = getattr(self, field)
            if not math.isfinite(value) or not 0 < value <= 1:
                raise ValueError(f'{field} must be finite in (0, 1]')
        for field in ('harmonic_tolerance_cents', 'pitch_tolerance_cents'):
            value = getattr(self, field)
            if not math.isfinite(value) or not 0 < value < 50:
                raise ValueError(f'{field} must be finite in (0, 50)')
        if not 32000 <= self.sample_rate <= 192000 or not 16 <= self.frame_ms <= 256:
            raise ValueError('Unsupported sample rate or frame size')
        if not 1 <= self.hop_ms <= self.frame_ms or not 1 <= self.fft_padding <= 8:
            raise ValueError('Unsupported hop or FFT padding')
        if not self.min_note < self.max_note <= 127 or not 1 <= self.max_voices <= 3:
            raise ValueError('Unsupported pitch range or voice count')
        if not 2 <= self.minimum_harmonics <= self.harmonics <= 16:
            raise ValueError('Unsupported harmonic count')
        if not math.isfinite(self.max_frequency) or not 100 < self.max_frequency < self.sample_rate / 2:
            raise ValueError('Invalid maximum frequency')
        if not math.isfinite(self.gate_db) or not -100 <= self.gate_db < 0:
            raise ValueError('Invalid gate')
        if not self.stable_frames <= 100 or not self.quiet_rearm_frames <= 1000:
            raise ValueError('Excessive hold/rearm time')


@dataclass(frozen=True)
class Peak:
    frequency: float
    amplitude: float


@dataclass(frozen=True)
class Decision:
    notes: tuple[int, ...]
    reason: str


def peaks(frame: NDArray[np.float64], config: Config) -> tuple[tuple[Peak, ...], float]:
    """Hann spectrum with log-quadratic peak interpolation and tonal concentration."""
    size = len(frame)
    fft_size = 1 << (size * config.fft_padding - 1).bit_length()
    spectrum = np.abs(np.fft.rfft((frame - np.mean(frame)) * np.hanning(size), n=fft_size))
    power = spectrum * spectrum
    maximum_bin = min(len(spectrum) - 2, int(config.max_frequency * fft_size / config.sample_rate))
    candidates = np.flatnonzero((spectrum[1:maximum_bin] > spectrum[:maximum_bin - 1]) &
                               (spectrum[1:maximum_bin] >= spectrum[2:maximum_bin + 1])) + 1
    threshold = float(np.max(spectrum)) * config.peak_floor_ratio
    selected = candidates[spectrum[candidates] >= threshold]
    covered = np.zeros(len(spectrum), dtype=np.bool_)
    radius = math.ceil(2 * fft_size / size)
    result: list[Peak] = []
    for index in selected:
        left, center, right = np.log(np.maximum(spectrum[index - 1:index + 2], 1e-30))
        denominator = left - 2 * center + right
        offset = float(np.clip(.5 * (left - right) / denominator, -.5, .5)) if denominator != 0 else 0.0
        result.append(Peak((int(index) + offset) * config.sample_rate / fft_size, float(spectrum[index])))
        covered[max(0, index - radius):index + radius + 1] = True
    concentration = float(np.sum(power[covered]) / max(float(np.sum(power)), 1e-30))
    return tuple(result), concentration


def harmonic_indices(frequency: float, values: tuple[Peak, ...], config: Config) -> tuple[int, ...]:
    matches: dict[int, int] = {}
    for index, peak in enumerate(values):
        harmonic = round(peak.frequency / frequency)
        if 1 <= harmonic <= config.harmonics:
            cents = abs(1200 * math.log2(peak.frequency / (frequency * harmonic)))
            if cents <= config.harmonic_tolerance_cents:
                previous = matches.get(harmonic)
                if previous is None or peak.amplitude > values[previous].amplitude:
                    matches[harmonic] = index
    return tuple(matches.values())


def analyze(frame: NDArray[np.float64], config: Config) -> Decision:
    expected = config.sample_rate * config.frame_ms // 1000
    if frame.ndim != 1 or len(frame) != expected or not np.all(np.isfinite(frame)):
        raise ValueError('Expected one finite, complete mono frame')
    if float(np.max(np.abs(frame))) >= config.clipping_level:
        return Decision((), 'clipping')
    rms = float(np.sqrt(np.mean((frame - np.mean(frame)) ** 2)))
    if rms < 10 ** (config.gate_db / 20):
        return Decision((), 'quiet')
    values, concentration = peaks(frame, config)
    if not values or concentration < config.minimum_concentration:
        return Decision((), 'broadband_or_transient')
    floor = max(p.amplitude for p in values) * config.fundamental_floor_ratio
    explained: set[int] = set()
    notes: list[int] = []
    for index, peak in enumerate(values):
        if index in explained or peak.amplitude < floor:
            continue
        pitch = 69 + 12 * math.log2(peak.frequency / 440)
        note = round(pitch)
        if not config.min_note <= note <= config.max_note:
            continue
        if abs(pitch - note) * 100 > config.pitch_tolerance_cents:
            return Decision((), 'off_grid_or_unresolved')
        support = harmonic_indices(peak.frequency, values, config)
        independent = set(support) - explained
        if len(independent) < config.minimum_harmonics:
            return Decision((), 'insufficient_independent_harmonics')
        notes.append(note)
        explained.update(support)
        if len(notes) > config.max_voices:
            return Decision((), 'too_many_voices')
    total = sum(p.amplitude ** 2 for p in values)
    coverage = sum(values[i].amplitude ** 2 for i in explained) / max(total, 1e-30)
    if not notes or coverage < config.minimum_coverage or len(set(notes)) != len(notes):
        return Decision((), 'unexplained_spectrum')
    return Decision(tuple(sorted(notes)), 'candidate_not_certified')


def detect(samples: NDArray[np.float64], config: Config) -> tuple[tuple[float, tuple[int, ...]], ...]:
    """Causal offline simulation. Reject immediately; do not hold stale recognized notes."""
    if samples.ndim != 1 or not np.all(np.isfinite(samples)):
        raise ValueError('Expected finite mono audio')
    size = config.sample_rate * config.frame_ms // 1000
    hop = config.sample_rate * config.hop_ms // 1000
    result: list[tuple[float, tuple[int, ...]]] = [(0.0, ())]
    candidate: tuple[int, ...] = ()
    stable = quiet = 0
    blocked = False
    for end in range(size, len(samples) + 1, hop):
        decision = analyze(samples[end - size:end], config)
        quiet = quiet + 1 if decision.reason == 'quiet' else 0
        if decision.reason == 'too_many_voices':
            blocked = True
        if quiet >= config.quiet_rearm_frames:
            blocked = False
        next_candidate = () if blocked else decision.notes
        stable = stable + 1 if next_candidate == candidate else 1
        candidate = next_candidate
        output = candidate if stable >= config.stable_frames else ()
        if output != result[-1][1]:
            result.append((1000 * end / config.sample_rate, output))
    return tuple(result)
