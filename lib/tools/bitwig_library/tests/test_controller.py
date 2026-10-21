"""Run controller models without requiring a live Bitwig instance."""
from pathlib import Path
import subprocess
import json
import re
import tomllib

import pytest


@pytest.mark.parametrize("script", ["controller_test.cjs", "key_sync_test.cjs", "keystation_test.cjs", "levels_test.cjs"])
def test_controller_model(script: str) -> None:
    result = subprocess.run(
        ["node", str(Path(__file__).with_name(script))],
        check=True, capture_output=True, text=True,
    )
    assert "PASS:" in result.stdout


def test_ambient_guitar_names_match_controller() -> None:
    root = Path(__file__).parents[1]
    config = tomllib.loads((root / "ambient_guitar.toml").read_text())
    source = (root / "Library.config.js").read_text()
    match = re.search(r"UTRP_LIBRARY_GUITAR_NAMES\s*=\s*(\[[^;]+\]);", source)
    assert match is not None
    names = json.loads(match.group(1))
    assert names == [preset["name"] for preset in config["presets"]]
    assert len(names) == len(set(names)) == 4
    assert config["group"] == "Ambient Guitar"
    assert 0 < config["track_gain_normalized"] < 1
    for preset in config["presets"]:
        assert 0 < preset["hall"]["decay"] <= 10
        assert 0 <= preset["hall"]["late"] <= 100
        if "delay" in preset:
            assert 0 <= preset["delay"]["feedback"] < 0.5
            assert 0 < preset["delay"]["mix"] < 1
