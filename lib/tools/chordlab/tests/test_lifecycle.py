"""Run current library lifecycle simulations alongside engine theme tests."""
from pathlib import Path
import subprocess

import pytest


@pytest.mark.parametrize("script", (
    "lib/tools/library/test_mode.lua",
))
def test_lua_lifecycle(script: str) -> None:
    root = Path(__file__).resolve().parents[4]
    result = subprocess.run(
        ["lua", script], cwd=root, check=True, capture_output=True, text=True,
    )
    assert "assertions passed" in result.stdout


def test_key_selection_notifies_host_for_project_scale_sync() -> None:
    source = (Path(__file__).resolve().parents[1] / "midi.jsfx-inc").read_text()
    assert "slider1=key; sliderchange(1); slider_automate(1);" in source
