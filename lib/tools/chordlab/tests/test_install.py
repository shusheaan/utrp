from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("chordlab_install", SOURCE / "install.py")
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_update_preserves_other_settings() -> None:
    text = "[REAPER]\nhello=42\n[vkb]\nchannel=0\nsize=100\n[Next]\nchannel=9\n"
    result = module.update_section(text, "vkb", {"channel": "15", "arrowen": "0"})
    assert result == "[REAPER]\nhello=42\n[vkb]\nsize=100\nchannel=15\narrowen=0\n[Next]\nchannel=9\n"


def test_missing_section_and_missing_key_restore() -> None:
    result = module.update_section("[REAPER]\nx=1\n", "vkb", {"channel": "15"})
    assert module.section_values(result, "vkb") == {"channel": "15"}
    assert module.section_values(module.update_section(result, "vkb", {"channel": None}), "vkb") == {}


def test_theme_is_generated_consistently() -> None:
    assert module.make_theme(SOURCE) == (SOURCE / "theme.jsfx-inc").read_text()


def test_mapping_is_exact_and_unique() -> None:
    rows = [line.split() for line in (SOURCE / "reaper-vkbmap.txt").read_text().splitlines()
            if line and not line.startswith(";")]
    mapping = {int(key): int(note) for key, note in rows}
    assert len(mapping) == len(rows) == 24
    assert sorted(mapping.values()) == list(range(23)) + [25]
    assert mapping[ord("D")] == 14 and mapping[13] == 22 and mapping[9] == 25


def test_install_and_restore_without_map(tmp_path: Path) -> None:
    original = "[REAPER]\nx=1\n[vkb]\nchannel=2\nnotecenter=48\n"
    (tmp_path / "reaper.ini").write_text(original)
    module.install(SOURCE, tmp_path)
    module.install(SOURCE, tmp_path)  # Idempotent; does not overwrite original backup.
    assert module.section_values((tmp_path / "reaper.ini").read_text(), "vkb")["channel"] == "15"
    module.uninstall(SOURCE, tmp_path)
    assert module.section_values((tmp_path / "reaper.ini").read_text(), "vkb") == {"channel": "2", "notecenter": "48"}
    assert not (tmp_path / "reaper-vkbmap.txt").exists()


def test_restore_existing_map_and_refuse_conflicting_directory(tmp_path: Path) -> None:
    (tmp_path / "reaper.ini").write_text("[REAPER]\nx=1\n")
    (tmp_path / "reaper-vkbmap.txt").write_text("old map\n")
    module.install(SOURCE, tmp_path)
    module.uninstall(SOURCE, tmp_path)
    assert (tmp_path / "reaper-vkbmap.txt").read_text() == "old map\n"
    (tmp_path / "Effects/ChordLab").mkdir()
    with pytest.raises(FileExistsError):
        module.install(SOURCE, tmp_path)


def test_only_runtime_assets_are_installed(tmp_path: Path) -> None:
    (tmp_path / "reaper.ini").write_text("[REAPER]\nx=1\n")
    module.install(SOURCE, tmp_path)
    effects = tmp_path / "Effects/ChordLab"
    assert not effects.is_symlink()
    assert sorted(p.name for p in effects.glob("*.jsfx")) == ["chordlab.jsfx"]
    assert not (effects / "tests").exists()
    assert len(list((tmp_path / "Scripts/ChordLab").iterdir())) == 4


@pytest.mark.parametrize("had_map", [False, True])
def test_uninstall_modified_map_does_not_change_ini(tmp_path: Path, had_map: bool) -> None:
    (tmp_path / "reaper.ini").write_text("[vkb]\nchannel=2\n")
    mapping = tmp_path / "reaper-vkbmap.txt"
    if had_map:
        mapping.write_text("original\n")
    module.install(SOURCE, tmp_path)
    before = (tmp_path / "reaper.ini").read_bytes()
    mapping.write_text("user changed this\n")
    with pytest.raises(RuntimeError, match="changed since install"):
        module.uninstall(SOURCE, tmp_path)
    assert (tmp_path / "reaper.ini").read_bytes() == before
    assert mapping.read_text() == "user changed this\n"


def test_reinstall_refuses_modified_map(tmp_path: Path) -> None:
    (tmp_path / "reaper.ini").write_text("[vkb]\nchannel=2\n")
    module.install(SOURCE, tmp_path)
    before = (tmp_path / "reaper.ini").read_bytes()
    (tmp_path / "reaper-vkbmap.txt").write_text("custom layout\n")
    with pytest.raises(RuntimeError, match="changed since install"):
        module.install(SOURCE, tmp_path)
    assert (tmp_path / "reaper.ini").read_bytes() == before
    assert (tmp_path / "reaper-vkbmap.txt").read_text() == "custom layout\n"


def test_upgrade_adds_missing_known_runtime_assets(tmp_path: Path) -> None:
    (tmp_path / "reaper.ini").write_text("[REAPER]\nx=1\n")
    module.install(SOURCE, tmp_path)
    for name in ("staff.jsfx-inc", "notation.png"):
        (tmp_path / "Effects/ChordLab" / name).unlink()
    module.install(SOURCE, tmp_path)
    for name in ("staff.jsfx-inc", "notation.png"):
        assert (tmp_path / "Effects/ChordLab" / name).resolve() == SOURCE / name
