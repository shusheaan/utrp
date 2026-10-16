"""Run the Lua host simulations alongside the installer regression tests."""
from pathlib import Path
import subprocess

import pytest


@pytest.mark.parametrize("script", (
    "lib/tools/chordlab/tests/test_mode.lua",
    "lib/tools/library/test_mode.lua",
))
def test_lua_lifecycle(script: str) -> None:
    root = Path(__file__).resolve().parents[4]
    result = subprocess.run(
        ["lua", script], cwd=root, check=True, capture_output=True, text=True,
    )
    assert "assertions passed" in result.stdout
