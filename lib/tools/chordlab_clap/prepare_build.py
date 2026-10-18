"""Prepare verified, offline dependencies and unchanged embedded Chord Lab assets."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path
import shutil
import tarfile
import tempfile
import tomllib
import zipfile
from port_upstream import port


@dataclass(frozen=True)
class Dependency:
    name: str
    url: str
    sha256: str
    destination: str


def dependencies(config: Path) -> tuple[Dependency, ...]:
    return tuple(Dependency(**entry) for entry in tomllib.loads(config.read_text())["dependency"])


def extract(archive: Path, destination: Path) -> None:
    with tempfile.TemporaryDirectory() as scratch:
        with tarfile.open(archive) as source:
            source.extractall(scratch, filter="data")
        roots = tuple(Path(scratch).iterdir())
        if len(roots) != 1 or not roots[0].is_dir():
            raise ValueError(f"Expected one source root: {archive}")
        shutil.copytree(roots[0], destination, dirs_exist_ok=True)


def patch_midi(adapter: Path) -> None:
    path = adapter / "src/wrapper/clap-juce-wrapper.cpp"
    text = path.read_text()
    old = "if (msg.getRawDataSize() == 3)"
    new = "if (msg.getRawDataSize() >= 1 && msg.getRawDataSize() <= 3 && !msg.isSysEx())"
    if text.count(old) != 1:
        raise ValueError("Pinned CLAP adapter no longer matches short-MIDI patch")
    text = text.replace(old, new).replace(
        "memcpy(&evt.data, msg.getRawData(), 3 * sizeof(uint8_t));",
        "memcpy(&evt.data, msg.getRawData(), static_cast<size_t>(msg.getRawDataSize()));")
    end = """                        ov->try_push(ov, reinterpret_cast<const clap_event_header *>(&evt));
                    }
                }
            }

            if (!midiBuffer.isEmpty())"""
    replacement = """                        ov->try_push(ov, reinterpret_cast<const clap_event_header *>(&evt));
                    }
                    else if (msg.isSysEx())
                    {
                        clap_event_midi_sysex evt{};
                        evt.header.size = sizeof(evt);
                        evt.header.type = CLAP_EVENT_MIDI_SYSEX;
                        evt.header.space_id = CLAP_CORE_EVENT_SPACE_ID;
                        evt.header.time = uint32_t(meta.samplePosition + n);
                        evt.port_index = 0;
                        evt.buffer = msg.getRawData();
                        evt.size = uint32_t(msg.getRawDataSize());
                        ov->try_push(ov, &evt.header);
                    }
                }
            }

            if (!midiBuffer.isEmpty())"""
    if text.count(end) != 1:
        raise ValueError("Pinned CLAP adapter no longer matches SysEx patch")
    path.write_text(text.replace(end, replacement))


def patch_global_parameters(adapter: Path) -> None:
    path = adapter / "src/wrapper/clap-juce-wrapper.cpp"
    text = path.read_text()
    old = "                evt.value = pc.newval;"
    new = old + "\n                evt.note_id = -1;\n                evt.port_index = evt.channel = evt.key = -1;"
    if text.count(old) != 1 or "evt.note_id = -1;\n                evt.port_index" in text:
        raise ValueError("Pinned CLAP adapter no longer matches global-parameter patch")
    text = text.replace(old, new)
    for kind in ('CLAP_EVENT_PARAM_VALUE', 'CLAP_EVENT_PARAM_GESTURE_BEGIN', 'CLAP_EVENT_PARAM_GESTURE_END'):
        before = 'uiParamChangeQ.push({' + kind + ', 0, id,'
        if text.count(before) != 1:
            raise ValueError("Pinned CLAP adapter no longer matches live-parameter patch")
        text = text.replace(before, 'uiParamChangeQ.push({' + kind + ', CLAP_EVENT_IS_LIVE, id,')
    path.write_text(text)


def assets(source: Path, destination: Path, config: Path) -> None:
    names = tomllib.loads(config.read_text())["source"]["assets"]
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in names:
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(entry, (source / name).read_bytes())


def keyboard_map(source: Path, destination: Path) -> None:
    pairs = tuple(tuple(map(int, line.split())) for line in source.read_text().splitlines()
                  if line.strip() and not line.startswith(";"))
    if len(set(key for key, _ in pairs)) != len(pairs):
        raise ValueError("Duplicate keyboard mapping")
    entries = ",\n".join(f"    KeyBinding{{{key}, {60 + offset}}}" for key, offset in pairs)
    destination.write_text("#pragma once\n#include <array>\n"
                           "struct KeyBinding { int key; int note; };\n"
                           f"inline constexpr std::array<KeyBinding, {len(pairs)}> chordlabKeys{{{{\n"
                           + entries + "\n}};\n")


def prepare(downloads: Path, output: Path, here: Path) -> None:
    deps = dependencies(here / "dependencies.toml")
    for dep in deps:
        path = downloads / f"{dep.name}.tar.gz"
        if hashlib.sha256(path.read_bytes()).hexdigest() != dep.sha256:
            raise ValueError(f"Dependency SHA-256 mismatch: {dep.name}")
    if output.exists():
        raise FileExistsError(f"Refusing to replace {output}")
    output.mkdir(parents=True)
    for dep in deps:
        extract(downloads / f"{dep.name}.tar.gz", output / dep.destination)
    patch_midi(output / "clap-juce")
    patch_global_parameters(output / "clap-juce")
    port(output / "ysfx", here)
    assets(here.parent / "chordlab", output / "chordlab.zip", here / "prototype.toml")
    keyboard_map(here / "keyboard-map.txt", output / "keyboard_map.h")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--downloads", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.downloads, args.output, Path(__file__).resolve().parent)


if __name__ == "__main__":
    main()
