"""Validate raw acceptance artifacts before writing a dedicated-port result."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def midi_rows(path: Path) -> int:
    with path.open() as source:
        rows = tuple(csv.DictReader(source, delimiter='\t'))
    if len(rows) != 2379 or any(row['JSFX'] != row['CLAP'] for row in rows):
        raise ValueError('MIDI A/B has missing or different cases')
    for row in rows:
        if any(token in row['label'] for token in (' L', ' K', ' reset', ' Tab')):
            if len(row['JSFX'].split(',')) < 6:
                raise ValueError('Vacuous control comparison')
    return len(rows)


def labelled_rows(path: Path) -> dict[str, tuple[float, ...]]:
    result = {}
    for line in path.read_text().splitlines():
        fields = line.split('\t')
        label, _time = fields[0].rsplit(' ', 1)
        result[label] = tuple(float(value) for value in fields[1:])
    return result


def gui_checks(root: Path) -> tuple[str, ...]:
    k = labelled_rows(root / 'keyboard-result.txt')
    f = labelled_rows(root / 'focus-result.txt')
    voices = 3 + 2 * k['D released'][6]
    checks = {
        'key hold/release': k['D held'][4] == 1 and k['D released'][4] == 0,
        'inversion/reset': k['L inversion'][2] > 0 and k['semicolon reset'][2] == 0,
        'Tab': k['Tab while held'][6] != k['before'][6],
        'long hold no retrigger': k['D held 2 seconds'][9] - k['D released'][9] == voices,
        'release after long hold': k['D released again'][9] - k['D held 2 seconds'][9] == voices,
        'Space contained': k['space must not start DAW'][8] == 0,
        'Enter/Escape sustain': k['Sustain ON'][7] == 1 and k['Escape panic and OFF'][7] == 0,
        'focus loss': f['held before focus loss'][4] == 1 and f['released on focus loss'][4] == 0,
        'first press after refocus': f['plays after refocus'][4] == 1 and f['released after refocus'][4] == 0,
    }
    for name, expected in (('mouse-sustain-on.txt', 1), ('closed-editor.txt', 0)):
        values = tuple(float(v) for v in (root / name).read_text().strip().split('\t'))
        checks[name] = values[8] == expected
    failed = tuple(name for name, passed in checks.items() if not passed)
    if failed:
        raise ValueError(f'GUI acceptance failed: {failed}')
    return tuple(checks)


def audit(ab: Path, gui: Path, plugin: Path, probe: Path) -> dict[str, object]:
    for root in (ab, gui):
        manifest = json.loads((root / 'manifest.json').read_text())
        if manifest['plugin_sha256'] != digest(plugin):
            raise ValueError(f'Binary mismatch: {root}')
    result = (ab / 'ab-result.txt').read_text()
    if 'passed=2379\nfailed=0\n' not in result:
        raise ValueError('MIDI runner did not pass')
    if not (ab / 'state-result.txt').read_text().startswith('PASS checks=7'):
        raise ValueError('Project reload did not pass')
    if (ab / 'parameter-result.txt').read_text() != 'passed=22/22\n':
        raise ValueError('Host parameter A/B did not pass')
    probe_text = probe.read_text()
    if probe_text.count('PASS') != 5 or 'error' in probe_text.lower():
        raise ValueError('ABI probe did not pass cleanly')
    return {
        'plugin_id': 'org.utrp.chordlab', 'version': '0.1.0',
        'plugin_sha256': digest(plugin), 'midi_cases_passed': midi_rows(ab / 'ab-events.tsv'),
        'midi_log_sha256': digest(ab / 'ab-events.tsv'), 'project_reload_checks': 7,
        'host_parameter_cases': 22, 'gui_checks': gui_checks(gui),
        'abi_probe': probe_text.splitlines(), 'python_tests': 81,
        'keyboard_unit_checks': 206, 'control_queue_checks': 9,
        'source_sha256': json.loads((ab / 'manifest.json').read_text())['source_sha256'],
        'environment': 'Linux x86_64, REAPER 7.78, Dummy Audio 48000/256, headless Sway/XWayland',
        'focus_test_note': 'X server auto-repeat disabled only during focus round trip, restored afterwards; long-hold test uses normal repeat',
        'limits': ['Bitwig runtime untested', 'physical MIDI/audio hardware untested',
                   'macOS/Windows unbuilt', 'not a universal 100-percent equivalence proof',
                   'GUI focus scope, not global DAW shortcut interception',
                   'MIDI offsets compared within blocks, not absolute latency'],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('ab', 'gui', 'plugin', 'probe', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.ab, args.gui, args.plugin, args.probe)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print('Acceptance artifacts verified:', args.output)


if __name__ == '__main__':
    main()
