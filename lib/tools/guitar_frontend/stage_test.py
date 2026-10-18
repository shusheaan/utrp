"""Stage an isolated REAPER integration test; never edits the user's profile."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil


def stage(plugin: Path, chordlab: Path, root: Path) -> None:
    if root.exists():
        raise FileExistsError(root)
    if root.parent != Path('/tmp') or not root.name.startswith('guitar-frontend-'):
        raise ValueError('Use a new /tmp/guitar-frontend-* directory')
    here = Path(__file__).resolve().parent
    plugins = root / 'plugins'
    profile = root / 'reaper'
    effects = profile / 'Effects/GuitarFrontendTest'
    effects.mkdir(parents=True)
    plugins.mkdir()
    (root / 'home/.config').mkdir(parents=True)
    hashes: dict[str, str] = {}
    for source in (plugin, chordlab):
        if source.suffix != '.clap' or not source.is_file():
            raise ValueError(f'Expected built CLAP: {source}')
        shutil.copyfile(source, plugins / source.name)
        hashes[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
    for name in ('test_source.jsfx', 'test_capture.jsfx'):
        shutil.copyfile(here / name, effects / name)
    shutil.copyfile(here / 'reaper_test.lua', profile / 'test.lua')
    (profile / 'reaper.ini').write_text(
        '[reaper]\nlinux_audio_mode=2\nlinux_audio_nch_in=0\nlinux_audio_nch_out=2\n'
        'linux_audio_srate=48000\nlinux_audio_bsize=256\n'
        f'clap_path_linux-x86_64={plugins}\nverchk=0\nshowlastproj=0\n'
        'midiins=0\nmidiins_h=0\nmidiins_x=0\nmidiins_x_h=0\n')
    (root / 'test.rpp').write_text('<REAPER_PROJECT 0.1 7 0\n>\n')
    (root / 'manifest.json').write_text(json.dumps(hashes, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin', type=Path, required=True)
    parser.add_argument('--chordlab', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    stage(args.plugin.resolve(), args.chordlab.resolve(), args.output)
