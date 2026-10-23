from __future__ import annotations

import json
from pathlib import Path
import sys
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog import document, policy_names, read_catalog


def fixture(tmp_path: Path, change: tuple[str, str] | None = None) -> tuple[Path, Path]:
    policy = tmp_path / 'policy.js'
    policy.write_text('const UTRP_LIBRARY_SOUND_NAMES = ["Piano"];\n'
                      'const UTRP_LIBRARY_GUITAR_NAMES = ["Guitar"];\n')
    xml = '''<Project><Structure><Track name="Keys"><Channel id="bus" destination="master">
      <Devices><BuiltinDevice deviceID="native" deviceName="Reverb">
        <Enabled value="true"/></BuiltinDevice></Devices></Channel>
      <Track name="Piano" loaded="true"><Channel id="piano" destination="bus">
        <Volume value="0.794328"/><Pan value="0.5"/><Devices>
        <Vst3Plugin deviceID="sfizz-id" deviceName="sfizz"><State path="plugins/piano"/>
        </Vst3Plugin></Devices></Channel></Track></Track>
      <Track name="Guitars"><Channel id="guitars" destination="master"/>
        <Track name="Guitar" loaded="false"><Channel id="guitar" destination="guitars">
          <Devices><ClapPlugin deviceID="hall-id" deviceName="Hall">
            <State path="plugins/hall"/></ClapPlugin></Devices></Channel></Track></Track>
      <Track name="Master"><Channel id="master"/></Track>
      </Structure></Project>'''
    if change is not None:
        xml = xml.replace(*change)
    project = tmp_path / 'test.dawproject'
    with zipfile.ZipFile(project, 'w') as archive:
        archive.writestr('project.xml', xml)
        archive.writestr('plugins/piano', b'sfizz preset')
        archive.writestr('plugins/hall', b'hall preset')
    return project, policy


def test_group_state_route_and_active_are_preserved(tmp_path: Path) -> None:
    project, policy = fixture(tmp_path)
    rows = read_catalog(project, policy)
    assert len(rows) == 2
    assert rows[0].groups == ('Keys',)
    assert rows[0].kind == 'piano' and rows[0].active
    assert not rows[1].active and rows[1].kind == 'guitar'
    assert tuple(r.name for r in rows[0].route) == ('Piano', 'Keys', 'Master')
    assert rows[0].route[0].gain == pytest.approx(0.794328)
    assert rows[0].bitwig_dependencies == ('Keys: Reverb',)
    assert rows[1].bitwig_dependencies == ()
    assert rows[0].route[0].devices[0].preset == 'plugins/piano'
    assert len(rows[0].route[0].devices[0].sha256 or '') == 64
    data = document(project, rows)
    assert json.loads(json.dumps(data))['active'] == {'piano': ['Piano'], 'guitar': []}
    assert data['playback_verified'] is False


@pytest.mark.parametrize('change,match', [
    (('destination="master"', 'destination="absent"'), 'Unknown channel'),
    (('id="master"', 'id="master" destination="piano"'), 'Cyclic'),
    (('id="guitar"', 'id="piano"'), 'Duplicate channel'),
    (('name="Piano"', 'name="Removed"'), 'Missing Library'),
    (('name="Master"', 'name="Piano"'), 'Ambiguous Library'),
    (('value="0.794328"', 'value="nan"'), 'Invalid Volume'),
    (('value="0.5"', 'value="2"'), 'Invalid Pan'),
    (('loaded="true"', 'loaded="maybe"'), 'Invalid boolean'),
    (('plugins/piano', '../outside'), 'Unsafe archive'),
    (('<State path="plugins/piano"/>', ''), 'Missing plugin preset'),
    (('Vst3Plugin', 'OtherPlugin'), 'Unsupported device'),
])
def test_invalid_catalog_fails_explicitly(tmp_path: Path, change: tuple[str, str],
                                        match: str) -> None:
    project, policy = fixture(tmp_path, change)
    with pytest.raises(ValueError, match=match):
        read_catalog(project, policy)


@pytest.mark.parametrize('value', ['[]', '[1]', '[""]', '["a", "a"]'])
def test_policy_is_validated(value: str) -> None:
    with pytest.raises(ValueError):
        policy_names(f'const TEST = {value};', 'TEST')


def test_disabled_native_device_not_a_dependency(tmp_path: Path) -> None:
    project, policy = fixture(tmp_path, ('value="true"', 'value="false"'))
    assert read_catalog(project, policy)[0].bitwig_dependencies == ()
