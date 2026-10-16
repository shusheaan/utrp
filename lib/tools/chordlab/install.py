#!/usr/bin/env python3
"""Install only Chord Lab assets and its explicit VKB map; back up before changing."""
from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path

VKB = {"channel": "15", "notecenter": "60", "arrowen": "0"}


def section_values(text: str, section: str) -> dict[str, str]:
    active = False
    values: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("["):
            active = line == f"[{section}]"
        elif active and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def update_section(text: str, section: str, changes: dict[str, str | None]) -> str:
    """Preserve unrelated settings byte-for-byte (apart from final newline)."""
    lines = text.splitlines(keepends=True)
    header = f"[{section}]"
    start = next((i for i, line in enumerate(lines) if line.strip() == header), -1)
    if start < 0:
        suffix = "" if not text or text.endswith("\n") else "\n"
        body = "".join(f"{k}={v}\n" for k, v in changes.items() if v is not None)
        return text + suffix + header + "\n" + body
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("[")), len(lines))
    body = [line for line in lines[start + 1:end] if line.partition("=")[0] not in changes]
    body.extend(f"{k}={v}\n" for k, v in changes.items() if v is not None)
    return "".join(lines[:start + 1] + body + lines[end:])


def make_theme(source: Path) -> str:
    raw = tomllib.loads((source / "theme.toml").read_text())
    lines = ["// Generated from theme.toml by install.py. Do not edit independently.", "@init"]
    for role in ("root", "third", "fifth", "seventh", "ninth", "external", "background", "button",
                 "button_hover", "button_selected", "text", "text_muted", "text_selected"):
        color = raw[role]
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise ValueError(f"Invalid {role} color")
        lines.append(f"{role}_color=$x{color[1:].upper()};")
    scale = raw["font_scale"]
    if not isinstance(scale, (int, float)) or not 1 <= scale <= 2:
        raise ValueError("font_scale must be in 1..2")
    lines.append(f"font_scale={scale};")
    return "\n".join(lines) + "\n"


def ensure_stopped(resource: Path) -> None:
    default = Path.home() / ".config/REAPER"
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            args = (entry / "cmdline").read_bytes().split(b"\0")
        except (FileNotFoundError, ProcessLookupError):
            continue  # A process exited during the /proc snapshot.
        if not args or Path(args[0].decode(errors="replace")).name != "reaper":
            continue
        profile = default
        if b"-cfgfile" in args:
            index = args.index(b"-cfgfile") + 1
            if index >= len(args):
                raise ValueError("REAPER process has an invalid -cfgfile argument")
            profile = Path(args[index].decode()).parent
        if profile.resolve() == resource.resolve():
            raise RuntimeError(f"Close REAPER using {resource} before installing/uninstalling")


def link_new(target: Path, source: Path) -> None:
    if target.is_symlink() and target.resolve() == source.resolve():
        return
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"Refusing to replace {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source, target_is_directory=source.is_dir())


def assets(source: Path, resource: Path) -> dict[Path, tuple[Path, ...]]:
    effects = tuple(source / name for name in (
        "chordlab.jsfx", "harmony.jsfx-inc", "midi.jsfx-inc", "ui.jsfx-inc", "theme.jsfx-inc", "staff.jsfx-inc", "notation.png",
    ))
    scripts = tuple(source / name for name in ("Open Chord Lab.lua", "Chord Lab mode.lua", "Register Chord Lab.lua", "Cycle chord type.lua"))
    return {resource / "Effects/ChordLab": effects, resource / "Scripts/ChordLab": scripts}


def validate_assets(layout: dict[Path, tuple[Path, ...]]) -> None:
    for directory, sources in layout.items():
        if not directory.exists() and not directory.is_symlink():
            continue
        if directory.is_symlink() or not directory.is_dir():
            raise FileExistsError(f"Refusing to replace {directory}")
        existing = {p.name for p in directory.iterdir()}
        if not existing or not existing <= {p.name for p in sources}:
            raise FileExistsError(f"Unmanaged contents in {directory}")
        for source in sources:
            target = directory / source.name
            if target.name not in existing:
                continue  # Add newly introduced runtime assets to a managed installation.
            if not target.is_symlink() or target.resolve() != source.resolve():
                raise FileExistsError(f"Refusing to replace {target}")


def install(source: Path, resource: Path) -> None:
    ini = resource / "reaper.ini"
    text = ini.read_text()
    backup = resource / "chordlab-backup"
    mapping = resource / "reaper-vkbmap.txt"
    layout = assets(source, resource)
    validate_assets(layout)
    theme = make_theme(source)  # Validate before touching the user's profile.
    if not backup.exists():
        backup.mkdir()
        (backup / "reaper.ini").write_text(text)
        old = section_values(text, "vkb")
        manifest = {"vkb": {key: old.get(key) for key in VKB}, "map_existed": mapping.exists()}
        if mapping.exists():
            (backup / "reaper-vkbmap.txt").write_bytes(mapping.read_bytes())
        (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    elif not (backup / "manifest.json").is_file():
        raise RuntimeError(f"Incomplete backup: {backup}; inspect before retrying")
    else:
        installed_map = backup / "installed-vkbmap.txt"
        if not installed_map.is_file():
            raise RuntimeError(f"Incomplete installed-map backup: {backup}")
        if mapping.exists() and mapping.read_bytes() != installed_map.read_bytes():
            raise RuntimeError("VKB map changed since install; refusing to overwrite it")
    (source / "theme.jsfx-inc").write_text(theme)
    for directory, sources in layout.items():
        for file in sources:
            link_new(directory / file.name, file)
    mapping.write_bytes((source / "reaper-vkbmap.txt").read_bytes())
    (backup / "installed-vkbmap.txt").write_bytes(mapping.read_bytes())
    ini.write_text(update_section(text, "vkb", VKB))
    print(f"Installed Chord Lab; original settings saved in {backup}")


def uninstall(source: Path, resource: Path) -> None:
    backup = resource / "chordlab-backup"
    manifest = json.loads((backup / "manifest.json").read_text())
    ini = resource / "reaper.ini"
    mapping = resource / "reaper-vkbmap.txt"
    layout = assets(source, resource)
    validate_assets(layout)
    if mapping.exists() and mapping.read_bytes() != (backup / "installed-vkbmap.txt").read_bytes():
        raise RuntimeError("VKB map changed since install; refusing to overwrite it")
    original_map = (backup / "reaper-vkbmap.txt").read_bytes() if manifest["map_existed"] else None
    restored_ini = update_section(ini.read_text(), "vkb", manifest["vkb"])
    if original_map is not None:
        mapping.write_bytes(original_map)
    elif mapping.exists():
        mapping.unlink()
    ini.write_text(restored_ini)
    for directory, sources in layout.items():
        if directory.exists():
            for file in sources:
                (directory / file.name).unlink()
            directory.rmdir()
    print(f"Restored original VKB settings. Backup retained: {backup}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource", type=Path, required=True)
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    resource = args.resource.expanduser().resolve()
    ensure_stopped(resource)
    source = Path(__file__).resolve().parent
    if args.uninstall:
        uninstall(source, resource)
    else:
        install(source, resource)


if __name__ == "__main__":
    main()
