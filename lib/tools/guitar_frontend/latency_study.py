"""Compare detector-only configurations without editing or installing the live plugin."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib

from configure import generate


@dataclass(frozen=True)
class Variant:
    name: str
    frame_ms: int
    hop_ms: int
    stability_ms: int

    @classmethod
    def from_mapping(cls, row: dict[str, object]) -> 'Variant':
        if set(row) != {'name', 'frame_ms', 'hop_ms', 'stability_ms'}:
            raise ValueError('Unexpected variant fields')
        name = row['name']
        if not isinstance(name, str) or re.fullmatch(r'[a-z0-9][a-z0-9-]*', name) is None:
            raise ValueError('Unsafe variant directory name')
        values: list[int] = []
        for key in ('frame_ms', 'hop_ms', 'stability_ms'):
            value = row[key]
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError('Variant timing values must be integers')
            values.append(value)
        return cls(name, values[0], values[1], values[2])


def variant_defaults(original: str, variant: Variant) -> str:
    result = original
    for field, value in (('frame_ms', variant.frame_ms), ('hop_ms', variant.hop_ms),
                         ('stability_ms', variant.stability_ms)):
        result, count = re.subn(rf'^{field} = .+$', f'{field} = {value}', result, flags=re.MULTILINE)
        if count != 1:
            raise ValueError(f'Expected one {field} setting')
    return result


def run(config_path: Path, destination: Path) -> None:
    source = Path(__file__).resolve().parent
    document = tomllib.loads(config_path.read_text())
    if set(document) != {'variants'} or not isinstance(document['variants'], list):
        raise ValueError('Expected [[variants]]')
    variants = tuple(Variant.from_mapping(row) for row in document['variants'])
    if not variants or len({v.name for v in variants}) != len(variants):
        raise ValueError('Variant names must be nonempty and unique')
    destination.mkdir(parents=True, exist_ok=True)
    original = (source / 'defaults.toml').read_text()
    results: list[dict[str, object]] = []
    for variant in variants:
        build = (destination / variant.name).resolve()
        build.mkdir(exist_ok=True)
        defaults = build / 'defaults.toml'
        defaults.write_text(variant_defaults(original, variant))
        generate(defaults, build / 'defaults.h')
        for target, filename in (('engine-tests', 'engine_tests.cpp'), ('replay-clip', 'replay_clip.cpp')):
            subprocess.run(['c++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Wpedantic', '-Werror',
                            '-I', str(source), '-I', str(build), str(source / 'engine.cpp'),
                            str(source / filename), '-o', str(build / target)], check=True)
        process = subprocess.run([str(build / 'engine-tests')], capture_output=True, text=True)
        output = process.stdout + process.stderr
        (build / 'test.txt').write_text(output)
        result = {'variant': variant.name, 'frame_ms': variant.frame_ms, 'hop_ms': variant.hop_ms,
                  'stability_ms': variant.stability_ms, 'returncode': process.returncode,
                  'passed_existing_detector_suite': process.returncode == 0, 'output': output}
        results.append(result)
        print(json.dumps(result), flush=True)
    hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
              for name in ('engine.cpp', 'engine.h', 'engine_tests.cpp', 'defaults.toml')}
    report = {'scope': 'Offline detector-only timing study; not hardware or host certification',
              'source_sha256': hashes, 'production_modified': False, 'results': results}
    (destination / 'results.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    run(Path(sys.argv[1]), Path(sys.argv[2]))
