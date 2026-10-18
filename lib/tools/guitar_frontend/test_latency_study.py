from pathlib import Path
import tomllib

import pytest

from configure import generate
from latency_study import Variant, variant_defaults


def test_variant_changes_only_selected_timings(tmp_path: Path) -> None:
    original = Path(__file__).with_name('defaults.toml').read_text()
    variant = Variant.from_mapping({'name': 'candidate', 'frame_ms': 40, 'hop_ms': 4, 'stability_ms': 8})
    candidate = variant_defaults(original, variant)
    before, after = tomllib.loads(original), tomllib.loads(candidate)
    before['analysis']['frame_ms'] = 40
    before['analysis']['hop_ms'] = 4
    before['parameters']['stability_ms'] = 8
    assert after == before
    source = tmp_path / 'defaults.toml'
    source.write_text(candidate)
    generate(source, tmp_path / 'defaults.h')


@pytest.mark.parametrize('name', ['../bad', '/tmp/bad', '', '.hidden', 'has space'])
def test_reject_unsafe_variant_names(name: str) -> None:
    with pytest.raises(ValueError):
        Variant.from_mapping({'name': name, 'frame_ms': 40, 'hop_ms': 4, 'stability_ms': 8})


@pytest.mark.parametrize('value', [True, '40', 40.0, None])
def test_reject_noninteger_timing(value: object) -> None:
    with pytest.raises(ValueError):
        Variant.from_mapping({'name': 'candidate', 'frame_ms': value, 'hop_ms': 4, 'stability_ms': 8})


def test_invalid_frame_is_rejected_by_existing_config_validator(tmp_path: Path) -> None:
    original = Path(__file__).with_name('defaults.toml').read_text()
    source = tmp_path / 'defaults.toml'
    source.write_text(variant_defaults(original, Variant('bad', 16, 4, 8)))
    with pytest.raises(ValueError):
        generate(source, tmp_path / 'defaults.h')


def test_missing_or_duplicate_setting_is_not_silently_replaced() -> None:
    with pytest.raises(ValueError):
        variant_defaults('hop_ms = 8\n', Variant('bad', 40, 4, 8))
    with pytest.raises(ValueError):
        variant_defaults('frame_ms = 64\nframe_ms = 64\n', Variant('bad', 40, 4, 8))
