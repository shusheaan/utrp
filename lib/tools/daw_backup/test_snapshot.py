from pathlib import Path
import tarfile

import pytest

from snapshot import Config, allowed, archive, sha256, working_files, run


def test_configuration() -> None:
    config = Config.read(Path(__file__).with_name('backup.toml'))
    assert config.backup_root == 'storage/daw/Recovery'
    assert '.BitwigStudio/prefs' in config.required
    assert not any('.activation' in name for name in config.required)


def test_retired_audio_services_are_not_restored() -> None:
    config = Config.read(Path(__file__).with_name('backup.toml'))
    entries = (*config.required, *config.optional)
    for name in ('utrp-audio-output.service', 'utrp-guitar-input.service'):
        assert not any(name in entry for entry in entries)
    assert '.config/systemd/user/utrp-plugin-windows.service' in config.required


@pytest.mark.parametrize('name', ['reaper-license.rk', '.activation-12', '__pycache__', 'cache.pyc'])
def test_private_or_generated_excluded(name: str) -> None:
    assert allowed(tarfile.TarInfo(name)) is None


def test_license_notices_preserved() -> None:
    assert allowed(tarfile.TarInfo('LICENSE')) is not None


@pytest.mark.parametrize("extension", [".tar", ".tar.gz"])
def test_archive_materializes_links(tmp_path: Path, extension: str) -> None:
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'config').write_text('custom setting')
    (source / 'alias').symlink_to(source / 'config')
    (source / 'reaper-license.rk').write_text('private')
    output = tmp_path / f'snapshot{extension}'
    archive(output, ((source, 'settings'),))
    with tarfile.open(output) as saved:
        assert saved.getmember('settings/alias').isfile()
        payload = saved.extractfile('settings/alias')
        assert payload is not None
        assert payload.read() == b'custom setting'
        assert 'settings/reaper-license.rk' not in saved.getnames()
    assert len(sha256(output)) == 64


def test_working_tree_includes_untracked_excludes_ignored(tmp_path: Path) -> None:
    run(['git', 'init'], tmp_path)
    (tmp_path / '.gitignore').write_text('generated\n')
    (tmp_path / 'pending.py').write_text('source')
    (tmp_path / 'generated').write_text('cache')
    paths = {path.name for path in working_files(tmp_path)}
    assert 'pending.py' in paths
    assert 'generated' not in paths


def test_config_rejects_traversal(tmp_path: Path) -> None:
    path = tmp_path / 'invalid.toml'
    source = Path(__file__).with_name('backup.toml').read_text()
    path.write_text(source.replace('storage/daw/Recovery', '../outside'))
    with pytest.raises(ValueError, match='safe home-relative'):
        Config.read(path)


def test_vendor_absolute_links_preserved(tmp_path: Path) -> None:
    link = tmp_path / 'launcher'
    link.symlink_to('/missing/vendor/install/path')
    output = tmp_path / 'runtime.tar'
    archive(output, ((link, 'usr/bin/vendor'),), dereference=False)
    with tarfile.open(output) as saved:
        assert saved.getmember('usr/bin/vendor').issym()
        assert saved.getmember('usr/bin/vendor').linkname == '/missing/vendor/install/path'


def test_runtime_root_link_resolved_but_vendor_links_preserved(tmp_path: Path) -> None:
    storage = tmp_path / 'Storage'
    storage.mkdir()
    (storage / 'content').write_text('installed package')
    (storage / 'vendor-link').symlink_to('/missing/vendor/resource')
    home_entry = tmp_path / 'installed-packages'
    home_entry.symlink_to(storage, target_is_directory=True)
    output = tmp_path / 'runtime.tar'
    # Same entry construction as snapshot's optional home-runtime archive.
    archive(output, ((home_entry.resolve(strict=True), home_entry.name),), dereference=False)
    with tarfile.open(output) as saved:
        assert saved.getmember('installed-packages').isdir()
        assert saved.getmember('installed-packages/content').isfile()
        assert saved.getmember('installed-packages/vendor-link').issym()


def test_completed_snapshot_updates_latest_without_losing_full(tmp_path: Path,
                                                             monkeypatch: pytest.MonkeyPatch) -> None:
    import snapshot as module
    home = tmp_path / 'home'
    (home / 'prefs').mkdir(parents=True)
    (home / 'prefs/settings').write_text('current')
    repo = tmp_path / 'repo'
    repo.mkdir()
    config = Config('Recovery', ('prefs',), (), (), (), ())

    def fake_run(command: list[str], cwd: Path) -> str:
        return 'test inventory\n'

    def no_sources(root: Path) -> tuple[Path, ...]:
        return ()

    monkeypatch.setattr(module, 'run', fake_run)
    monkeypatch.setattr(module, 'working_files', no_sources)
    full = module.snapshot(config, repo, home, True)
    latest = module.snapshot(config, repo, home, False)
    assert (home / 'Recovery/LATEST').read_text().strip() == latest.name
    assert (home / 'Recovery/LATEST_FULL').read_text().strip() == full.name
    assert not (latest / 'INCOMPLETE').exists()
    assert (latest / 'manifest.json').is_file()
    assert not list((home / 'Recovery').glob('*.tmp'))
