import json
from types import SimpleNamespace

import httpx
import pytest

from hito12.common import ROOT, read_json
from hito12.dataset import aggregate, generate, rows_for_match
from hito12.load import run_load
from tests.test_dataset import small_config


@pytest.mark.parametrize('corrupt', [False, True])
def test_runner_exports_and_aborts_on_wrong_result(monkeypatch, tmp_path, corrupt):
    """Transporte y métricas simulados: verifica el runner, NO mide InfluxDB."""
    cfg = read_json(ROOT / 'config/humo.json')
    dataset = small_config()
    manifest = generate(dataset, tmp_path / 'dataset')
    def handler(request):
        match = request.url.path.split('/')[4]
        resolution = request.url.params['resolucion']
        rows = aggregate(list(rows_for_match(dataset, int(match[1:]))), resolution)
        if corrupt:
            rows[0]['tiros_intervalo'] += 1
        return httpx.Response(200, json={'data': {'partido_id': match, 'desde': manifest['from'],
            'hasta': manifest['to'], 'resolucion': resolution, 'items': rows, 'truncado': False}},
            headers={'X-Hito12-Lab': 'hito12-g09', 'X-Api-Ms': '1', 'X-Dependency-Ms': '0.5'})
    sample = {'Name': 'hito12-g09-api-1', 'MemPerc': '10%', 'CPUPerc': '1%'}
    monkeypatch.setattr('hito12.load.command', lambda *a, **k: '\n'.join(json.dumps(sample) for _ in range(2)))
    monkeypatch.setattr('hito12.load.psutil.virtual_memory', lambda: SimpleNamespace(available=4 * 2**30))
    monkeypatch.setattr('hito12.load.psutil.cpu_percent', lambda: 1.0)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = run_load(client, cfg, manifest, tmp_path / 'run', {'api': 'fake-api', 'influxdb': 'fake-db'})
    assert result['aborted'] is corrupt
    assert (tmp_path / 'run/requests.csv').is_file()
    assert (tmp_path / 'run/resources.json').is_file()
    if corrupt:
        assert result['all_phases']['integrity_errors'] >= 1
    else:
        assert result['steady']['successful'] > 0
        assert result['steady']['errors'] == 0
        assert result['observed_operations'] == result['planned_operations']
