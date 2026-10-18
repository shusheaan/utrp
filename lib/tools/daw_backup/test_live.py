from pathlib import Path
import subprocess

import pytest

from live import Config, apply, entry, plan, relative_path, require_closed


def config() -> Config:
    return Config('storage/daw/UserData', ('prefs',), ('BitwigStudio',))


def test_real_config() -> None:
    value = Config.read(Path(__file__).with_name('live.toml'))
    assert len(value.directories) == 10
    assert '.BitwigStudio/prefs' in value.directories
    assert '.config' not in value.directories


def test_move_identity_atomic_save_idempotence_and_relink(tmp_path: Path) -> None:
    source = tmp_path / 'prefs'
    source.mkdir()
    settings = source / 'settings.xml'
    settings.write_text('old')
    original = settings.stat()
    (source / 'internal-link').symlink_to('settings.xml')
    apply(plan(config(), tmp_path))
    target = tmp_path / config().root / 'prefs'
    assert source.is_symlink()
    assert settings.stat().st_ino == original.st_ino
    assert (target / 'internal-link').readlink() == Path('settings.xml')
    temp = source / 'temporary.xml'
    temp.write_text('new')
    temp.replace(settings)
    assert (target / 'settings.xml').read_text() == 'new'
    assert all(item.action == 'linked' for item in plan(config(), tmp_path))
    apply(plan(config(), tmp_path))
    source.unlink()  # Simulate reinstalled home: data in Storage remains intact.
    assert plan(config(), tmp_path)[0].action == 'relink'
    apply(plan(config(), tmp_path))
    assert settings.read_text() == 'new'


def test_collision_does_not_overwrite(tmp_path: Path) -> None:
    source, target = tmp_path / 'prefs', tmp_path / config().root / 'prefs'
    source.mkdir()
    target.mkdir(parents=True)
    with pytest.raises(FileExistsError):
        plan(config(), tmp_path)
    assert not source.is_symlink()


def test_missing_and_unexpected_links(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        plan(config(), tmp_path)
    (tmp_path / 'prefs').symlink_to(tmp_path / 'missing')
    with pytest.raises(FileExistsError, match='broken home link'):
        plan(config(), tmp_path)


def test_target_link_rejected(tmp_path: Path) -> None:
    target = tmp_path / 'target'
    target.symlink_to(tmp_path / 'missing')
    with pytest.raises(FileExistsError, match='real directory'):
        entry(tmp_path / 'source', target)


@pytest.mark.parametrize('value', ['../bad', '/absolute', '', '.', 123])
def test_unsafe_path(value: object) -> None:
    with pytest.raises(ValueError):
        relative_path(value)


def test_nested_config_rejected(tmp_path: Path) -> None:
    path = tmp_path / 'config.toml'
    path.write_text('root="storage"\ndirectories=["prefs", "prefs/nested"]\nblocked_processes=[]\n')
    with pytest.raises(ValueError, match='Overlapping'):
        Config.read(path)


def test_active_daw_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    def running(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(['ps'], 0, 'BitwigStudio\n')
    monkeypatch.setattr(subprocess, 'run', running)
    with pytest.raises(RuntimeError, match='Close audio'):
        require_closed(config())
