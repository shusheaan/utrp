"""Stage the dedicated CLAP beside unchanged JSFX, in a scratch-only REAPER profile."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tomllib


def stage(plugin: Path, output: Path, here: Path) -> Path:
    if not plugin.is_file() or plugin.suffix != '.clap':
        raise ValueError('Expected a built Linux .clap file')
    if output.exists():
        raise FileExistsError(f'Refusing to replace {output}')
    output = output.resolve()
    settings = tomllib.loads((here / 'prototype.toml').read_text())
    source = here.parent / 'chordlab'
    hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
              for name in settings['source']['assets']}
    profile = output / 'reaper'
    assets = profile / 'Effects/ChordLab'
    assets.mkdir(parents=True)
    for name in hashes:
        shutil.copyfile(source / name, assets / name)
    for name in ('ab_source.jsfx', 'ab_capture.jsfx'):
        shutil.copyfile(here / name, assets / name)
    for name in ('ab_test.lua', 'state_ab.lua', 'parameter_ab.lua', 'mixed_ab.lua', 'mixed_record.lua'):
        shutil.copyfile(here / name, profile / name)
    plugins = output / 'plugins'
    plugins.mkdir()
    shutil.copyfile(plugin, plugins / 'Chord Lab.clap')
    (output / 'home/.config').mkdir(parents=True)
    audio = settings['audio']
    (profile / 'reaper.ini').write_text(
        '[reaper]\nlinux_audio_mode=2\nlinux_audio_nch_in=0\nlinux_audio_nch_out=2\n'
        f"linux_audio_srate={audio['sample_rate']}\nlinux_audio_bsize={audio['block_size']}\n"
        f'clap_path_linux-x86_64={plugins}\nverchk=0\nshowlastproj=0\n'
        'midiins=0\nmidiins_h=0\nmidiins_x=0\nmidiins_x_h=0\n')
    (output / 'wrapper-track.txt').write_text(
        '<TRACK\nNAME "B - Chord Lab CLAP"\nMAINSEND 0\n<FXCHAIN\nSHOW 0\nBYPASS 0 0 0\n'
        '<CLAP "CLAP: Chord Lab (UTRP)" org.utrp.chordlab ""\n>\nWAK 0 0\n>\n>\n')
    (output / 'prototype.rpp').write_text('<REAPER_PROJECT 0.1 7 0\n>\n')
    (output / 'manifest.json').write_text(json.dumps({
        'plugin_id': 'org.utrp.chordlab', 'version': '0.1.6',
        'plugin_sha256': hashlib.sha256(plugin.read_bytes()).hexdigest(),
        'source_sha256': hashes, 'status': 'dedicated port; awaiting acceptance',
    }, indent=2) + '\n')
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(stage(args.plugin, args.output, Path(__file__).resolve().parent))


if __name__ == '__main__':
    main()
