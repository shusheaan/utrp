"""Validate Surge FXP payloads and stage a one-shot native REAPER library build."""
from __future__ import annotations

import argparse
import base64
import json
import struct
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path


def surge_payload(data: bytes) -> bytes:
    if len(data) < 92 or (data[:4], data[8:12], data[16:20], data[60:64]) != (
        b"CcnK", b"FPCh", b"cjs3", b"sub3"
    ):
        raise ValueError("Not a supported Surge chunk FXP")
    size = struct.unpack_from(">I", data, 56)[0]
    xml_size = struct.unpack_from("<I", data, 64)[0]
    if size != len(data) - 60 or not 0 < xml_size <= len(data) - 92:
        raise ValueError("Invalid Surge chunk length")
    root = ET.fromstring(data[92:92 + xml_size])
    if root.tag != "patch" or root.find("parameters") is None:
        raise ValueError("Missing Surge patch parameters")
    return data[60:]  # Includes XML AND every embedded wavetable, not just parameters.


def resolve(value: str, base: Path) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else base / path).resolve()


def prepare(config: Path, staging: Path) -> None:
    settings = tomllib.loads(config.read_text())
    root = resolve(settings["patch_root"], config.parent)
    destination = resolve(settings["project"], config.parent)
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite edited library: {destination}")
    patches = [(p.parent.name, p.stem, p) for p in sorted(root.rglob("*.fxp"))]
    patches += [(v["collection"], v["name"], resolve(v["source"], config.parent))
                for v in settings.get("variants", [])]
    if not patches or len({(g, n) for g, n, _ in patches}) != len(patches):
        raise ValueError("Empty library or duplicate patch names")
    for key in ("track_volume", "master_volume"):
        if not 0 < settings[key] <= 1:
            raise ValueError(f"Invalid {key}")
    # Validate every payload before writing any staging file.
    payloads = [(g, n, p, surge_payload(p.read_bytes())) for g, n, p in patches]
    staging.mkdir(parents=True, exist_ok=False)
    entries: list[str] = []
    for i, (group, name, path, payload) in enumerate(payloads):
        target = staging / f"{i:03}.b64"
        target.write_text(base64.b64encode(payload).decode("ascii"))
        fields = {"group": group, "name": name, "path": str(path), "state": str(target)}
        entries.append("{" + ",".join(f"{k}={json.dumps(v, ensure_ascii=False)}"
                                      for k, v in fields.items()) + "}")
    settings_text = ",\n".join(f"{key}={json.dumps(settings[key])}" for key in (
        "track_volume", "master_volume", "initial_patch"))
    manifest = staging / "manifest.lua"
    manifest.write_text(f"return {{destination={json.dumps(str(destination))},\n"
                        f"{settings_text},\npatches={{\n" + ",\n".join(entries) + "\n}}\n")
    builder = config.parent / "build.lua"
    (staging / "run.lua").write_text(
        f"dofile({json.dumps(str(builder.resolve()))})(dofile({json.dumps(str(manifest))}))\n")
    print(f"Staged {len(payloads)} patches: {staging / 'run.lua'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staging", type=Path)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("library.toml"))
    args = parser.parse_args()
    prepare(args.config.resolve(), args.staging.resolve())


if __name__ == "__main__":
    main()
