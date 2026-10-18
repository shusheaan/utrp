"""Move DAW user directories to Storage; home contains only directory symlinks."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import tomllib


def relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or value == '.':
        raise ValueError('Expected a nonempty relative path')
    path = Path(value)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError(f'Unsafe relative path: {value}')
    return str(path)


@dataclass(frozen=True)
class Config:
    root: str
    directories: tuple[str, ...]
    blocked_processes: tuple[str, ...]

    @classmethod
    def read(cls, path: Path) -> Config:
        data = tomllib.loads(path.read_text())
        root = relative_path(data['root'])
        dirs, blocked = data['directories'], data['blocked_processes']
        if not isinstance(dirs, list) or not dirs:
            raise ValueError('directories must be a nonempty list')
        if not isinstance(blocked, list) or not all(isinstance(s, str) and s for s in blocked):
            raise ValueError('blocked_processes must be a list of names')
        names = tuple(relative_path(v) for v in dirs)
        paths = tuple(Path(v) for v in (*names, root))
        for index, first in enumerate(paths):
            for second in paths[index + 1:]:
                if first.is_relative_to(second) or second.is_relative_to(first):
                    raise ValueError(f'Overlapping paths: {first}, {second}')
        return cls(root, names, tuple(blocked))


@dataclass(frozen=True)
class Entry:
    source: Path
    target: Path
    action: str


def entry(source: Path, target: Path) -> Entry:
    if target.is_symlink():
        raise FileExistsError(f'Storage target must be a real directory: {target}')
    if source.is_symlink():
        if source.resolve() == target.resolve() and target.is_dir():
            return Entry(source, target, 'linked')
        raise FileExistsError(f'Unexpected or broken home link: {source}')
    if source.exists():
        if not source.is_dir() or target.exists():
            raise FileExistsError(f'Refusing to overwrite/merge: {source} -> {target}')
        return Entry(source, target, 'move')
    if target.is_dir():
        return Entry(source, target, 'relink')
    raise FileNotFoundError(f'Neither home nor Storage directory exists: {source}')


def plan(config: Config, home: Path) -> tuple[Entry, ...]:
    root = home / config.root
    # A real persistent root must be present for subsequent runs / reinstall.
    if root.exists() and not root.is_dir():
        raise NotADirectoryError(root)
    result = tuple(entry(home / name, root / name) for name in config.directories)
    for item in result:
        ancestor = item.target.parent
        while not ancestor.exists():
            ancestor = ancestor.parent
        if root.exists() and not item.target.resolve().is_relative_to(root.resolve()):
            raise ValueError(f'Target escapes Storage root: {item.target}')
        if item.action == 'move' and item.source.stat().st_dev != ancestor.stat().st_dev:
            raise ValueError('Cross-filesystem move needs a separately verified copy; refusing rename')
    return result


def require_closed(config: Config) -> None:
    output = subprocess.run(['ps', '-eo', 'comm='], check=True, capture_output=True, text=True)
    found = set(output.stdout.splitlines()) & set(config.blocked_processes)
    if found:
        raise RuntimeError(f'Close audio applications first: {sorted(found)}')


def apply(entries: tuple[Entry, ...]) -> None:
    for item in entries:
        if item.action == 'linked':
            continue
        item.target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if item.action == 'move':
            item.source.rename(item.target)
        # If interrupted here, rerunning reconstructs the link (action=relink).
        item.source.parent.mkdir(parents=True, exist_ok=True)
        item.source.symlink_to(item.target, target_is_directory=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('live.toml'))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    config = Config.read(args.config)
    entries = plan(config, Path.home())
    for item in entries:
        print(f'{item.action}: {item.source} -> {item.target}')
    if args.apply:
        require_closed(config)
        apply(entries)
        entries = plan(config, Path.home())
    if args.check or args.apply:
        if any(item.action != 'linked' for item in entries):
            raise RuntimeError('Not all live directories are linked')
        print(f'OK: {len(entries)} live Storage directories')


if __name__ == '__main__':
    main()
