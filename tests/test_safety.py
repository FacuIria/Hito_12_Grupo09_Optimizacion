import copy
import json

import pytest

from hito12.common import containers, local_docker


def inspection(service):
    return {'Config': {'Image': 'image', 'Labels': {'com.docker.compose.project': 'hito12-g09',
                'com.docker.compose.service': service, 'edu.fixture.hito': '12'}},
            'State': {'Running': True, 'OOMKilled': False},
            'NetworkSettings': {'Networks': {'hito12-g09_laboratorio': {}}},
            'HostConfig': {'PortBindings': {'port/tcp': [{'HostIp': '127.0.0.1',
                          'HostPort': '8012' if service == 'api' else '18182'}]},
                          'Memory': 512*2**20 if service == 'api' else 2*2**30,
                          'NanoCpus': 10**9 if service == 'api' else 2*10**9},
            'Mounts': [] if service == 'api' else [{'Type': 'volume', 'Name': 'hito12-g09_datos_hito12'}],
            'Image': 'sha256:image', 'RestartCount': 0}


@pytest.mark.parametrize('change', ['network', 'volume', 'port', 'resources', 'label', 'stopped'])
def test_refuses_foreign_or_unbounded_container(monkeypatch, change):
    items = {'api': inspection('api'), 'influxdb': inspection('influxdb')}
    monkeypatch.setattr('hito12.common.compose', lambda *a: 'api\ninfluxdb')
    monkeypatch.setattr('hito12.common.command', lambda args: json.dumps([items[args[-1]]]))
    assert set(containers()) == {'api', 'influxdb'}
    db = items['influxdb']
    if change == 'network': db['NetworkSettings']['Networks'] = {'fixture2030-hito11-net': {}}
    if change == 'volume': db['Mounts'][0]['Name'] = 'original-volume'
    if change == 'port': db['HostConfig']['PortBindings']['port/tcp'][0]['HostIp'] = '0.0.0.0'
    if change == 'resources': db['HostConfig']['Memory'] = 0
    if change == 'label': db['Config']['Labels']['edu.fixture.hito'] = '11'
    if change == 'stopped': db['State']['Running'] = False
    with pytest.raises(RuntimeError):
        containers()


def test_remote_docker_refused_before_any_daemon_call(monkeypatch):
    monkeypatch.setenv('DOCKER_HOST', 'tcp://other-machine:2375')
    monkeypatch.setattr('hito12.common.command', lambda args: pytest.fail('No debe consultar el daemon'))
    with pytest.raises(RuntimeError, match='local'):
        local_docker()


def test_build_identity_covers_modules_and_normalizes_newlines(tmp_path):
    from app.build_info import build_info, text_hash
    info = build_info()
    assert {'main.py', 'adapter.py', 'upstream_influx3.py', 'build_info.py'} <= set(info['app_files_sha256'])
    assert info['packages']['httpx'] == '0.28.1'
    first, second = tmp_path / 'a.py', tmp_path / 'b.py'
    first.write_bytes(b'line1\r\nline2\r\n')
    second.write_bytes(b'line1\nline2\n')
    assert text_hash(first) == text_hash(second)


def test_metadata_refuses_stale_deployed_api(monkeypatch):
    from app.build_info import build_info
    from hito12.common import metadata
    stale = build_info()
    stale['app_files_sha256']['main.py'] = 'old-version'
    monkeypatch.setattr('hito12.common.local_docker', lambda: {})
    monkeypatch.setattr('hito12.common.containers', lambda: {'api': {'id': 'api'}, 'influxdb': {'id': 'db'}})
    def fake_command(args):
        if args[:2] == ['git', 'rev-parse']: return 'commit'
        if args[:2] == ['git', 'status']: return ''
        if args[:3] == ['docker', 'exec', 'db']: return 'InfluxDB fixture-version'
        if args[:3] == ['docker', 'exec', 'api']: return json.dumps(stale)
        pytest.fail('Comando inesperado')
    monkeypatch.setattr('hito12.common.command', fake_command)
    with pytest.raises(RuntimeError, match='API desplegada'):
        metadata()
