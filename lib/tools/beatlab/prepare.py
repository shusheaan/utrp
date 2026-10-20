"""Verify and unpack local dependency archives, without modifying another project."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path
import shutil
import tarfile
import tempfile
import tomllib


@dataclass(frozen=True)
class Dependency:
    name: str
    url: str
    sha256: str
    destination: str


def prepare(downloads: Path, output: Path) -> None:
    config = Path(__file__).with_name("dependencies.toml")
    deps = tuple(Dependency(**item) for item in tomllib.loads(config.read_text())["dependency"])
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    for dep in deps:
        archive = downloads / f"{dep.name}.tar.gz"
        if hashlib.sha256(archive.read_bytes()).hexdigest() != dep.sha256:
            raise ValueError(f"SHA-256 mismatch: {dep.name}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as scratch:
        staged = Path(scratch) / "deps"
        for dep in deps:
            with tempfile.TemporaryDirectory(dir=scratch) as unpacked:
                with tarfile.open(downloads / f"{dep.name}.tar.gz") as archive:
                    archive.extractall(unpacked, filter="data")
                roots = tuple(Path(unpacked).iterdir())
                if len(roots) != 1 or not roots[0].is_dir():
                    raise ValueError(f"Expected one source root: {dep.name}")
                shutil.copytree(roots[0], staged / dep.destination, dirs_exist_ok=True)
        staged.rename(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--downloads", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.downloads, args.output)


if __name__ == "__main__":
    main()
