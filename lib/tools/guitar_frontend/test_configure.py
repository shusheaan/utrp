from pathlib import Path

import pytest
from configure import generate


def test_defaults(tmp_path: Path) -> None:
    destination = tmp_path / 'defaults.h'
    generate(Path(__file__).with_name('defaults.toml'), destination)
    assert 'stability_ms = 24.0;' in destination.read_text()


@pytest.mark.parametrize(('before', 'after'), [
    ('confidence = 0.88', 'confidence = nan'),
    ('confidence = 0.88', 'confidence = inf'),
    ('confidence = 0.88', 'confidence = true'),
    ('confidence = 0.88', 'confidence = 1.1'),
    ('velocity = 90.0', 'velocity = 90.5'),
    ('velocity = 90.0', 'unknown = 90.0'),
    ('max_note = 88', 'max_note = 36'),
    ('min_note = 38', 'min_note = 24'),
    ('hop_ms = 8.0', 'hop_ms = 32.0\nextra = 1'),
    ('frame_ms = 64.0', 'frame_ms = 128.0'),
    ('lowpass_hz = 2200.0', 'lowpass_hz = 6000.0'),
    ('[analysis]', '[unexpected]'),
    ('fundamental_power_ratio = 0.02', 'fundamental_power_ratio = 0'),
    ('subharmonic_confidence = 0.60', 'subharmonic_confidence = nan'),
    ('spectral_margin = 1.20', 'spectral_margin = 0.9'),
    ('spectral_peak_cents = 30.0', 'spectral_peak_cents = 0'),
    ('spectral_peak_cents = 30.0', 'spectral_peak_cents = 51'),
    ('spectral_peak_cents = 30.0', 'spectral_peak_cents = nan'),
])
def test_reject_invalid(tmp_path: Path, before: str, after: str) -> None:
    source = tmp_path / 'bad.toml'
    destination = tmp_path / 'defaults.h'
    source.write_text(Path(__file__).with_name('defaults.toml').read_text().replace(before, after))
    destination.write_text('unchanged')
    with pytest.raises(ValueError):
        generate(source, destination)
    assert destination.read_text() == 'unchanged'
