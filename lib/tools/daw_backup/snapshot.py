"""Private, checksummed DAW recovery snapshot; never restores or overwrites live files."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tomllib


@dataclass(frozen=True)
class Config:
    backup_root: str
    required: tuple[str, ...]
    optional: tuple[str, ...]
    assets: tuple[str, ...]
    system_assets: tuple[str, ...]
    persistent: tuple[str, ...]

    @classmethod
    def read(cls, path: Path) -> Config:
        data = tomllib.loads(path.read_text())
        root = data['backup_root']
        if not isinstance(root, str):
            raise ValueError('backup_root must be a string')
        groups: list[tuple[str, ...]] = []
        for key in ('required', 'optional', 'assets', 'system_assets', 'persistent'):
            values = data[key]
            if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
                raise ValueError(f'{key} must contain path strings')
            groups.append(tuple(values))
        for value in (root, *groups[0], *groups[1], *groups[2], *groups[4]):
            if Path(value).is_absolute() or '..' in Path(value).parts:
                raise ValueError(f'Expected safe home-relative path: {value}')
        for value in groups[3]:
            if not Path(value).is_absolute() or '..' in Path(value).parts:
                raise ValueError(f'Expected absolute system path: {value}')
        return cls(root, *groups)


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(command: list[str], cwd: Path) -> str:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True).stdout


def working_files(repo: Path) -> tuple[Path, ...]:
    names = run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], repo)
    return tuple(repo / name for name in sorted(set(names.split('\0')) - {''})
                 if (repo / name).is_file())


def allowed(member: tarfile.TarInfo) -> tarfile.TarInfo | None:
    name = Path(member.name).name
    if name in {'__pycache__', '.pytest_cache'} or name.endswith(('.pyc', '-journal')):
        return None
    if name.startswith('.activation-') or name == 'reaper-license.rk':
        return None
    return member


def archive(destination: Path, entries: tuple[tuple[Path, str], ...],
            dereference: bool = True) -> None:
    # Dereference deployment symlinks so external gral sources are self-contained.
    with tarfile.open(destination, 'w' if destination.suffix == '.tar' else 'w:gz', dereference=dereference) as output:
        for source, name in entries:
            output.add(source, arcname=name, filter=allowed)
    # Read every payload to catch truncated/corrupt archives before success.
    with tarfile.open(destination, 'r:*') as check:
        for member in check:
            if member.isfile():
                stream = check.extractfile(member)
                if stream is None:
                    raise RuntimeError(f'Missing archive payload: {member.name}')
                with stream:
                    while stream.read(1024 * 1024):
                        pass


def snapshot(config: Config, repo: Path, home: Path, include_assets: bool) -> Path:
    required = tuple(home / name for name in config.required)
    missing = tuple(str(path) for path in required if not path.exists())
    if missing:
        raise FileNotFoundError(f'Missing required recovery inputs: {missing}')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    destination = home / config.backup_root / stamp
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    (destination / 'INCOMPLETE').write_text('Do not restore until manifest.json exists.\n')
    optional = tuple(home / name for name in config.optional if (home / name).exists())
    archive(destination / 'home-customizations.tar.gz',
            tuple((path, str(path.relative_to(home))) for path in required + optional))
    files = working_files(repo)
    archive(destination / 'utrp-working-tree.tar.gz',
            tuple((path, str(path.relative_to(repo))) for path in files))
    (destination / 'git-status.txt').write_text(run(['git', 'status', '--short'], repo))
    (destination / 'git-head.txt').write_text(run(['git', 'rev-parse', 'HEAD'], repo))
    if include_assets:
        assets = tuple(home / name for name in config.assets)
        archive(destination / 'home-runtime-assets.tar',
                tuple((path.resolve(strict=True), str(path.relative_to(home))) for path in assets),
                dereference=False)
        archive(destination / 'system-runtime-assets.tar',
                tuple((Path(name), str(Path(name).relative_to('/'))) for name in config.system_assets),
                dereference=False)
    project = home / 'storage/daw/Library/Library.bwproject'
    if project.exists():
        archive(destination / 'Library-saved-project.tar.gz', ((project, project.name),))
    for command, name in ((['pacman', '-Q'], 'packages.txt'), (['uname', '-a'], 'platform.txt')):
        (destination / name).write_text(run(command, repo))
    manifest = {
        'created_utc': stamp, 'home': str(home), 'repo': str(repo),
        'scope': 'DAW customization; excludes credentials, cache, and unsaved application memory',
        'symlinks': 'home customization links dereferenced; vendor runtime links preserved',
        'missing_optional': [name for name in config.optional if not (home / name).exists()],
        'persistent_paths': {name: (home / name).exists() for name in config.persistent},
        'assets_included': include_assets,
        'working_file_count': len(files),
        'sha256': {path.name: sha256(path) for path in sorted(destination.iterdir())
                   if path.is_file() and path.name != 'INCOMPLETE'},
    }
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (destination / 'INCOMPLETE').unlink()
    for name in (('LATEST', 'LATEST_FULL') if include_assets else ('LATEST',)):
        temporary = destination.parent / f'.{name}-{stamp}.tmp'
        temporary.write_text(stamp + '\n')
        temporary.replace(destination.parent / name)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-assets', action='store_true')
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('backup.toml'))
    arguments = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    print(snapshot(Config.read(arguments.config), repo, Path.home(), arguments.include_assets))


if __name__ == '__main__':
    main()
